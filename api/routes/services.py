"""
Service registry API routes.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from api.deps import extract_owner, require_provider

router = APIRouter(tags=["services"])


# --- Request/Response models ---

class RegisterServiceRequest(BaseModel):
    name: str
    description: str = ""
    endpoint: str
    price_per_call: str  # String to preserve decimal precision
    category: str = ""
    tags: list[str] = []
    payment_method: str = "x402"
    free_tier_calls: int = 0

    @field_validator("endpoint")
    @classmethod
    def endpoint_must_be_url(cls, v: str) -> str:
        if not v.startswith(("https://", "http://")):
            raise ValueError("Endpoint must be a valid URL")
        return v

    @field_validator("price_per_call")
    @classmethod
    def price_must_be_valid(cls, v: str) -> str:
        from decimal import Decimal, InvalidOperation
        try:
            price = Decimal(v)
        except InvalidOperation:
            raise ValueError("Price must be a valid decimal number")
        if price < 0:
            raise ValueError("Price cannot be negative")
        if price > Decimal("10000"):
            raise ValueError("Price cannot exceed $10,000 per call")
        return v


class UpdateServiceRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    endpoint: Optional[str] = None
    price_per_call: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None


# --- Routes ---

@router.post("/services", status_code=201)
async def register_service(req: RegisterServiceRequest, request: Request):
    """Register a new service on the marketplace. Requires API key."""
    from marketplace.registry import RegistryError

    provider_id, _ = require_provider(request)
    registry = request.app.state.registry
    try:
        service = registry.register(
            provider_id=provider_id,
            name=req.name,
            description=req.description,
            endpoint=req.endpoint,
            price_per_call=req.price_per_call,
            category=req.category,
            tags=req.tags,
            payment_method=req.payment_method,
            free_tier_calls=req.free_tier_calls,
        )
        resp = _service_response(service)
        # Include founding seller info if awarded
        founding = registry.get_founding_seller(provider_id)
        if founding:
            resp["founding_seller"] = founding
        return resp
    except RegistryError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/services")
async def list_services(
    request: Request,
    query: Optional[str] = None,
    category: Optional[str] = None,
    status: str = "active",
    limit: int = 50,
    offset: int = 0,
):
    """List or search services. No auth required."""
    registry = request.app.state.registry
    services = registry.search(
        query=query,
        category=category,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {
        "services": [_service_response(s) for s in services],
        "count": len(services),
        "offset": offset,
        "limit": limit,
    }


@router.get("/services/{service_id}")
async def get_service(service_id: str, request: Request):
    """Get service details. No auth required."""
    registry = request.app.state.registry
    service = registry.get(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return _service_response(service)


@router.patch("/services/{service_id}")
async def update_service(
    service_id: str,
    req: UpdateServiceRequest,
    request: Request,
):
    """Update a service (owner only). Requires API key."""
    from marketplace.registry import RegistryError

    provider_id, _ = require_provider(request)
    registry = request.app.state.registry
    updates = req.model_dump(exclude_none=True)

    try:
        service = registry.update(service_id, provider_id, **updates)
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        return _service_response(service)
    except RegistryError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/services/{service_id}")
async def delete_service(
    service_id: str,
    request: Request,
):
    """Remove a service (soft delete, owner only). Requires API key."""
    from marketplace.registry import RegistryError

    provider_id, _ = require_provider(request)
    registry = request.app.state.registry
    try:
        removed = registry.remove(service_id, provider_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Service not found")
        return {"status": "removed", "id": service_id}
    except RegistryError as e:
        raise HTTPException(status_code=403, detail=str(e))


# --- Founding Seller ---

@router.get("/founding-sellers")
async def list_founding_sellers(request: Request):
    """List all founding sellers (first 50 providers). No auth required."""
    registry = request.app.state.registry
    sellers = registry.list_founding_sellers()
    remaining = registry.founding_seller_spots_remaining()
    return {
        "founding_sellers": sellers,
        "count": len(sellers),
        "spots_remaining": remaining,
        "max_spots": 50,
    }


@router.get("/founding-sellers/{provider_id}")
async def get_founding_seller(provider_id: str, request: Request):
    """Check if a provider is a founding seller. No auth required."""
    registry = request.app.state.registry
    seller = registry.get_founding_seller(provider_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Not a founding seller")
    return seller


# --- Helpers ---

def _service_response(service) -> dict:
    """Convert ServiceListing to API response dict."""
    return {
        "id": service.id,
        "provider_id": service.provider_id,
        "name": service.name,
        "description": service.description,
        "pricing": {
            "price_per_call": str(service.pricing.price_per_call),
            "currency": service.pricing.currency,
            "payment_method": service.pricing.payment_method,
            "free_tier_calls": service.pricing.free_tier_calls,
        },
        "status": service.status,
        "category": service.category,
        "tags": list(service.tags),
        "created_at": service.created_at.isoformat(),
        "updated_at": service.updated_at.isoformat(),
    }
