"""MCP tool definitions (docs/04-mcp-server-spec.md, section 2).

Each tool is a thin, stateless proxy to the backend HTTP API
(docs/03-http-api-spec.md) and passes the JSON response through
unchanged.
"""

from typing import Any, Literal, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from client import get


def register_tools(mcp: FastMCP) -> None:
    """Register all tools from 04-mcp-server-spec.md on the FastMCP server."""

    @mcp.tool(
        name="get_daily_hot",
        description=(
            "Fetch the hot AI news list for a specific date and language. "
            "Returns the items[] list from GET /news/hot, sorted by hot_score."
        ),
    )
    async def get_daily_hot(
        date: Optional[str] = Field(
            default=None, description="YYYY-MM-DD, defaults to today"
        ),
        lang: Optional[str] = Field(
            default=None, description="Target language code, e.g. en, zh-TW"
        ),
        limit: int = Field(default=30, description="Max items"),
    ) -> Any:
        return await get(
            "/news/hot", params={"date": date, "lang": lang, "limit": limit}
        )

    @mcp.tool(
        name="search_news",
        description=(
            "Search AI news by natural language query and optional filters "
            "(date range, topic, language). Returns article summaries from "
            "GET /news/stream (items[])."
        ),
    )
    async def search_news(
        query: str = Field(min_length=1, description="Natural language query"),
        lang: Optional[str] = Field(default=None),
        from_: Optional[str] = Field(
            default=None,
            validation_alias="from",
            description="YYYY-MM-DD or ISO8601",
        ),
        to: Optional[str] = Field(default=None),
        topic: Optional[str] = Field(default=None),
        limit: int = Field(default=20),
    ) -> Any:
        return await get(
            "/news/stream",
            params={
                "q": query,
                "lang": lang,
                "from": from_,
                "to": to,
                "topic": topic,
                "limit": limit,
            },
        )

    @mcp.tool(
        name="get_article_detail",
        description=(
            "Get full detail for a selected article (content, topics, "
            "related cluster articles) from GET /news/{id}."
        ),
    )
    async def get_article_detail(
        id: str = Field(description="Article id"),
        lang: Optional[str] = Field(default=None),
    ) -> Any:
        return await get(f"/news/{id}", params={"lang": lang})

    @mcp.tool(
        name="get_insight",
        description=(
            "Fetch structured daily/weekly insights (AI highlights brief with "
            "sections and referenced articles) from GET /insights/daily."
        ),
    )
    async def get_insight(
        type: Literal["daily", "weekly"] = Field(default="daily"),
        date: Optional[str] = Field(
            default=None, description="YYYY-MM-DD; if null, latest"
        ),
        lang: Optional[str] = Field(default=None),
    ) -> Any:
        return await get(
            "/insights/daily",
            params={"type": type, "date": date, "lang": lang},
        )
