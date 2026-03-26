"""
Agent Commerce Framework Python SDK.

Provides a clean Python interface for all ACF marketplace operations,
wrapping the REST API so users don't need to deal with HTTP directly.
"""
from __future__ import annotations

from typing import Any, Optional

import httpx


class ACFError(Exception):
    """Error returned by the ACF API."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"ACF API error {status_code}: {message}")


class ACFClient:
    """Agent Commerce Framework Python SDK."""

    def __init__(
        self,
        base_url: str = "https://agentictrade.io",
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """
        Args:
            base_url: ACF server URL.
            api_key: API key in format "key_id:secret".
            timeout: HTTP request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        """Build request headers, including auth if configured."""
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Send an HTTP request and return the parsed JSON response.

        Raises ACFError on non-2xx status codes.
        """
        # Strip None values from query params
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        response = self._client.request(
            method,
            path,
            headers=self._headers(),
            json=json,
            params=params,
        )
        if response.status_code >= 400:
            # Try to extract detail from JSON response body
            try:
                body = response.json()
                detail = body.get("detail", response.text)
            except Exception:
                detail = response.text
            raise ACFError(response.status_code, detail)
        return response.json()

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "ACFClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def create_key(
        self,
        owner_id: str,
        role: str = "buyer",
        rate_limit: int | None = None,
    ) -> dict:
        """Create a new API key.

        Args:
            owner_id: Identifier for the key owner.
            role: Key role (buyer, provider, admin).
            rate_limit: Requests per minute limit.

        Returns:
            Dict with key_id, secret, role, rate_limit, and message.
        """
        payload: dict[str, Any] = {"owner_id": owner_id, "role": role}
        if rate_limit is not None:
            payload["rate_limit"] = rate_limit
        return self._request("POST", "/api/v1/keys", json=payload)

    def validate_key(self) -> dict:
        """Validate the currently configured API key.

        Returns:
            Dict with valid, owner_id, role, and rate_limit.

        Raises:
            ACFError: If no API key is configured or the key is invalid.
        """
        if not self.api_key:
            raise ACFError(401, "No API key configured")
        parts = self.api_key.split(":", 1)
        if len(parts) != 2:
            raise ACFError(401, "Invalid key format. Use key_id:secret")
        return self._request(
            "POST",
            "/api/v1/keys/validate",
            json={"key_id": parts[0], "secret": parts[1]},
        )

    # ------------------------------------------------------------------
    # Agent Identity
    # ------------------------------------------------------------------

    def register_agent(
        self,
        display_name: str,
        capabilities: list[str] | None = None,
        identity_type: str = "api_key_only",
        wallet_address: str | None = None,
    ) -> dict:
        """Register a new agent identity.

        Args:
            display_name: Human-readable agent name.
            capabilities: List of capability strings.
            identity_type: Identity verification type.
            wallet_address: Optional crypto wallet address.

        Returns:
            Agent details dict.
        """
        payload: dict[str, Any] = {
            "display_name": display_name,
            "identity_type": identity_type,
        }
        if capabilities is not None:
            payload["capabilities"] = capabilities
        if wallet_address is not None:
            payload["wallet_address"] = wallet_address
        return self._request("POST", "/api/v1/agents", json=payload)

    def get_agent(self, agent_id: str) -> dict:
        """Get agent details by ID."""
        return self._request("GET", f"/api/v1/agents/{agent_id}")

    def search_agents(self, query: str) -> list:
        """Search agents by name or ID."""
        result = self._request(
            "GET", "/api/v1/agents/search", params={"q": query}
        )
        return result.get("agents", [])

    def update_agent(self, agent_id: str, **kwargs: Any) -> dict:
        """Update an agent's details."""
        return self._request(
            "PATCH", f"/api/v1/agents/{agent_id}", json=kwargs
        )

    # ------------------------------------------------------------------
    # Services
    # ------------------------------------------------------------------

    def register_service(
        self,
        name: str,
        endpoint: str,
        price_per_call: str,
        category: str | None = None,
        tags: list[str] | None = None,
        payment_method: str = "x402",
        free_tier_calls: int = 0,
        **kwargs: Any,
    ) -> dict:
        """Register a new service on the marketplace.

        Args:
            name: Service name.
            endpoint: Service URL endpoint.
            price_per_call: Price per API call (string for decimal precision).
            category: Service category.
            tags: List of tags for discovery.
            payment_method: Payment method (x402, stripe, etc.).
            free_tier_calls: Number of free calls before payment required.

        Returns:
            Registered service details dict.
        """
        payload: dict[str, Any] = {
            "name": name,
            "endpoint": endpoint,
            "price_per_call": price_per_call,
            "payment_method": payment_method,
            "free_tier_calls": free_tier_calls,
        }
        if category is not None:
            payload["category"] = category
        if tags is not None:
            payload["tags"] = tags
        payload.update(kwargs)
        return self._request("POST", "/api/v1/services", json=payload)

    def list_services(self, status: str | None = None) -> list:
        """List services on the marketplace."""
        result = self._request(
            "GET", "/api/v1/services", params={"status": status}
        )
        return result.get("services", [])

    def get_service(self, service_id: str) -> dict:
        """Get service details by ID."""
        return self._request("GET", f"/api/v1/services/{service_id}")

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def search(
        self,
        query: str | None = None,
        category: str | None = None,
        min_price: str | None = None,
        max_price: str | None = None,
        has_free_tier: bool | None = None,
    ) -> dict:
        """Search for services with enhanced filters."""
        params: dict[str, Any] = {
            "q": query,
            "category": category,
            "min_price": min_price,
            "max_price": max_price,
            "has_free_tier": has_free_tier,
        }
        return self._request("GET", "/api/v1/discover", params=params)

    def get_categories(self) -> list:
        """Get all service categories with counts."""
        result = self._request("GET", "/api/v1/discover/categories")
        return result.get("categories", [])

    def get_trending(self, limit: int = 10) -> list:
        """Get trending services by usage volume."""
        result = self._request(
            "GET", "/api/v1/discover/trending", params={"limit": limit}
        )
        return result.get("trending", [])

    def get_recommendations(self, agent_id: str, limit: int = 5) -> list:
        """Get service recommendations for an agent."""
        result = self._request(
            "GET",
            f"/api/v1/discover/recommendations/{agent_id}",
            params={"limit": limit},
        )
        return result.get("recommendations", [])

    # ------------------------------------------------------------------
    # Proxy
    # ------------------------------------------------------------------

    def call_service(
        self,
        service_id: str,
        method: str = "GET",
        path: str = "/",
        body: dict | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict:
        """Call a service through the ACF proxy.

        The marketplace handles payment and forwards the request to the
        service provider.
        """
        clean_path = path.lstrip("/")
        proxy_path = f"/api/v1/proxy/{service_id}/{clean_path}"

        if params:
            params = {k: v for k, v in params.items() if v is not None}

        response = self._client.request(
            method,
            proxy_path,
            headers=self._headers(),
            json=body,
            params=params,
        )
        if response.status_code >= 400:
            try:
                error_body = response.json()
                detail = error_body.get("detail", response.text)
            except Exception:
                detail = response.text
            raise ACFError(response.status_code, detail)

        try:
            return response.json()
        except Exception:
            return {"body": response.text, "status_code": response.status_code}

    # ------------------------------------------------------------------
    # Reputation
    # ------------------------------------------------------------------

    def get_agent_reputation(
        self, agent_id: str, period: str = "all-time"
    ) -> dict:
        """Get reputation data for an agent."""
        return self._request(
            "GET",
            f"/api/v1/agents/{agent_id}/reputation",
            params={"period": period},
        )

    def get_leaderboard(self, limit: int = 10) -> list:
        """Get the reputation leaderboard."""
        result = self._request(
            "GET",
            "/api/v1/reputation/leaderboard",
            params={"limit": limit},
        )
        return result.get("leaderboard", [])

    # ------------------------------------------------------------------
    # Teams
    # ------------------------------------------------------------------

    def create_team(
        self, name: str, description: str | None = None
    ) -> dict:
        """Create a new team."""
        payload: dict[str, Any] = {"name": name}
        if description is not None:
            payload["description"] = description
        return self._request("POST", "/api/v1/teams", json=payload)

    def add_member(
        self,
        team_id: str,
        agent_id: str,
        role: str = "worker",
        skills: list[str] | None = None,
    ) -> dict:
        """Add a member to a team."""
        payload: dict[str, Any] = {"agent_id": agent_id, "role": role}
        if skills is not None:
            payload["skills"] = skills
        return self._request(
            "POST", f"/api/v1/teams/{team_id}/members", json=payload
        )

    def add_routing_rule(
        self,
        team_id: str,
        name: str,
        keywords: list[str],
        target_agent_id: str,
        priority: int = 10,
    ) -> dict:
        """Add a routing rule to a team."""
        payload: dict[str, Any] = {
            "name": name,
            "keywords": keywords,
            "target_agent_id": target_agent_id,
            "priority": priority,
        }
        return self._request(
            "POST", f"/api/v1/teams/{team_id}/rules", json=payload
        )

    # ------------------------------------------------------------------
    # Webhooks
    # ------------------------------------------------------------------

    def subscribe(self, url: str, events: list[str], secret: str) -> dict:
        """Create a webhook subscription."""
        payload: dict[str, Any] = {
            "url": url,
            "events": events,
            "secret": secret,
        }
        return self._request("POST", "/api/v1/webhooks", json=payload)

    def list_subscriptions(self) -> list:
        """List own webhook subscriptions."""
        result = self._request("GET", "/api/v1/webhooks")
        return result.get("webhooks", [])

    def unsubscribe(self, webhook_id: str) -> bool:
        """Delete a webhook subscription."""
        self._request("DELETE", f"/api/v1/webhooks/{webhook_id}")
        return True

    # ------------------------------------------------------------------
    # Settlements
    # ------------------------------------------------------------------

    def create_settlement(
        self,
        provider_id: str,
        period_start: str,
        period_end: str,
    ) -> dict:
        """Create a settlement for a provider (admin only)."""
        payload: dict[str, Any] = {
            "provider_id": provider_id,
            "period_start": period_start,
            "period_end": period_end,
        }
        return self._request("POST", "/api/v1/settlements", json=payload)

    def list_settlements(self) -> list:
        """List settlements."""
        result = self._request("GET", "/api/v1/settlements")
        return result.get("settlements", [])
