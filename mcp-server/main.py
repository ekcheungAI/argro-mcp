"""Entry point for the ai-news-mcp-server.

A stateless MCP server (streamable-HTTP transport) that proxies the
AI news backend HTTP API defined in docs/03-http-api-spec.md.
"""

import os

from mcp.server.fastmcp import FastMCP

from tools import register_tools

mcp = FastMCP(
    name="ai-news-mcp-server",
    instructions=(
        "Multi-source AI news and insights for agents: "
        "hot list, search, and structured daily briefs."
    ),
    stateless_http=True,
    json_response=True,
    streamable_http_path="/mcp",
    host=os.environ.get("MCP_SERVER_HOST", "0.0.0.0"),
    port=int(os.environ.get("MCP_SERVER_PORT", "8100")),
)

register_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
