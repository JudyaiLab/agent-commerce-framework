"""HTTP client for AgenticTrade API.

Encapsulates all network communication with the AgenticTrade marketplace.
Every public method returns plain dicts/lists — no side effects on the client
instance (immutable-friendly design).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("agentictrade_mcp.client")

_DEFAULT_BASE_URL = "https://agentictrade.io"
_DEFAULT_TIMEOUT = 30.0
_MAX_RESULTS_LIMIT = 100


class AgenticTradeError(Exception):
    """Raised when the AgenticTrade API returns an error response."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class AgenticTradeClient:
    """Async HTTP client for the AgenticTrade marketplace API.

    Parameters
    ----------
    base_url : str
        Root URL of the AgenticTrade instance (no trailing slash).
    timeout : float
        Default request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._http: httpx.AsyncClient | None = None

    async def _client(self) -> httpx.AsyncClient:
        """Lazily create and return the shared HTTP client."""
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={
                    "User-Agent": "agentictrade-mcp/0.1.0",
                    "Accept": "application/json",
                },
            )
        return self._http

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()
            self._http = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Perform an authenticated or unauthenticated GET request."""
        client = await self._client()
        resp = await client.get(path, params=params)
        if resp.status_code >= 400:
            detail = resp.text[:500]
            try:
                detail = resp.json().get("detail", detail)
            except Exception:
                pass
            raise AgenticTradeError(resp.status_code, detail)
        return resp.json()

    async def _get_authed(
        self, path: str, api_key: str, params: dict[str, Any] | None = None,
    ) -> Any:
        """Perform a GET request with Bearer authentication."""
        client = await self._client()
        resp = await client.get(
            path,
            params=params,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        if resp.status_code >= 400:
            detail = resp.text[:500]
            try:
                detail = resp.json().get("detail", detail)
            except Exception:
                pass
            raise AgenticTradeError(resp.status_code, detail)
        return resp.json()

    async def _post_authed(
        self,
        path: str,
        api_key: str,
        json_body: dict[str, Any] | None = None,
        raw_body: bytes | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        """POST with Bearer auth. Returns (status, headers, body)."""
        client = await self._client()
        headers: dict[str, str] = {"Authorization": f"Bearer {api_key}"}
        if raw_body is not None:
            headers["Content-Type"] = "application/octet-stream"
            resp = await client.post(path, content=raw_body, headers=headers)
        else:
            resp = await client.post(path, json=json_body or {}, headers=headers)

        resp_headers = dict(resp.headers)
        return resp.status_code, resp_headers, resp.content

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    async def discover_services(
        self,
        query: str | None = None,
        category: str | None = None,
        max_results: int = 20,
    ) -> dict[str, Any]:
        """Search/browse available API services on the marketplace.

        Returns dict with ``services`` list and ``total`` count.
        """
        params: dict[str, Any] = {
            "limit": min(max(max_results, 1), _MAX_RESULTS_LIMIT),
        }
        if query:
            params["q"] = query
        if category:
            params["category"] = category

        return await self._get("/api/v1/discover", params=params)

    async def get_service_details(self, service_id: str) -> dict[str, Any]:
        """Get full details of a specific service by ID."""
        if not service_id or not service_id.strip():
            raise ValueError("service_id is required")
        return await self._get(f"/api/v1/services/{service_id}")

    async def call_service(
        self,
        service_id: str,
        api_key: str,
        payload: dict[str, Any] | None = None,
        path: str = "",
        method: str = "POST",
    ) -> dict[str, Any]:
        """Call an API service through the AgenticTrade payment proxy.

        Returns dict with ``status_code``, ``body``, and billing headers.
        """
        if not service_id or not service_id.strip():
            raise ValueError("service_id is required")
        if not api_key or not api_key.strip():
            raise ValueError("api_key is required")

        proxy_path = f"/api/v1/proxy/{service_id}"
        if path:
            clean_path = path.lstrip("/")
            proxy_path = f"{proxy_path}/{clean_path}"

        status_code, headers, body = await self._post_authed(
            proxy_path,
            api_key,
            json_body=payload,
        )

        # Extract billing headers
        billing = {
            "usage_id": headers.get("x-acf-usage-id", ""),
            "amount_usd": headers.get("x-acf-amount", "0"),
            "free_tier": headers.get("x-acf-free-tier", "false"),
            "latency_ms": headers.get("x-acf-latency-ms", "0"),
        }

        # Try to parse body as JSON
        response_body: Any
        try:
            import json
            response_body = json.loads(body)
        except Exception:
            response_body = body.decode("utf-8", errors="replace")

        return {
            "status_code": status_code,
            "body": response_body,
            "billing": billing,
        }

    async def get_balance(self, api_key: str, buyer_id: str) -> dict[str, Any]:
        """Check agent's USDC balance.

        Returns dict with ``buyer_id``, ``balance``, ``total_deposited``,
        ``total_spent``.
        """
        if not api_key or not api_key.strip():
            raise ValueError("api_key is required")
        if not buyer_id or not buyer_id.strip():
            raise ValueError("buyer_id is required")
        return await self._get_authed(
            f"/api/v1/balance/{buyer_id}",
            api_key,
        )

    async def list_categories(self) -> dict[str, Any]:
        """List all service categories with service counts."""
        return await self._get("/api/v1/discover/categories")
