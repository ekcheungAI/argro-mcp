"""Async HTTP client for the AI news backend API (docs/03-http-api-spec.md).

The MCP server only talks to the backend over HTTP and never touches
the database directly.
"""

from typing import Any, Optional

import httpx
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    """Configuration for the backend HTTP API, read from environment.

    - ``MCP_BACKEND_URL``: base URL of the backend API (default http://localhost:8000).
    - ``API_KEY``: optional API key, sent as the ``X-API-Key`` header when set.
    """

    model_config = SettingsConfigDict(extra="ignore")

    backend_url: str = Field(
        default="http://localhost:8000", validation_alias="MCP_BACKEND_URL"
    )
    api_key: Optional[str] = Field(default=None, validation_alias="API_KEY")


settings = BackendSettings()


def _client() -> httpx.AsyncClient:
    headers = {}
    if settings.api_key:
        headers["X-API-Key"] = settings.api_key
    return httpx.AsyncClient(
        base_url=settings.backend_url.rstrip("/"),
        headers=headers,
        timeout=httpx.Timeout(30.0),
    )


async def get(path: str, params: Optional[dict[str, Any]] = None) -> Any:
    """GET ``path`` on the backend and return the decoded JSON body.

    - Drops query parameters whose value is ``None``.
    - Raises ``RuntimeError`` (with URL and status where relevant) on
      transport errors, HTTP status >= 400, or invalid JSON responses.
    """
    clean_params = {k: v for k, v in (params or {}).items() if v is not None}
    url = f"{settings.backend_url.rstrip('/')}{path}"

    async with _client() as client:
        try:
            response = await client.get(path, params=clean_params)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Backend request failed: GET {url}: {exc}") from exc

    if response.status_code >= 400:
        raise RuntimeError(
            f"Backend error: GET {url} returned HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Backend error: GET {url} returned HTTP {response.status_code} "
            f"with invalid JSON: {exc}"
        ) from exc
