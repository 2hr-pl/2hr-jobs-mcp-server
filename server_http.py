import os
import uvicorn
from mcp.server.fastmcp import FastMCP
from tools.search import register_search_tools
from tools.salary import register_salary_tools
from tools.analytics import register_analytics_tools
from resources.documentation import register_resources
from prompts.templates import register_prompts

mcp = FastMCP(
    name="2HR Jobs MCP Server",
    version="1.0.0",
)

register_search_tools(mcp)
register_salary_tools(mcp)
register_analytics_tools(mcp)
register_resources(mcp)
register_prompts(mcp)

app = mcp.get_asgi_app()

if __name__ == "__main__":
    uvicorn.run(
        "server_http:app",
        host=os.getenv("MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_PORT", "8765")),
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        workers=int(os.getenv("WORKERS", "1")),
    )
