import logging
import os
from mcp.server.fastmcp import FastMCP
from tools.search import register_search_tools
from tools.salary import register_salary_tools
from tools.analytics import register_analytics_tools
from resources.documentation import register_resources
from prompts.templates import register_prompts

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def create_server() -> FastMCP:
    mcp = FastMCP(
        name="2HR Jobs MCP Server",
        version="1.0.0",
    )
    register_search_tools(mcp)
    register_salary_tools(mcp)
    register_analytics_tools(mcp)
    register_resources(mcp)
    register_prompts(mcp)
    logger.info("MCP server configured — tools, resources and prompts registered")
    return mcp


if __name__ == "__main__":
    mcp = create_server()
    logger.info("Starting MCP server via stdio...")
    mcp.run()
