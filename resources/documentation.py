from mcp.server.fastmcp import FastMCP


def register_resources(mcp: FastMCP) -> None:

    @mcp.resource("docs://api/overview")
    def get_api_overview() -> str:
        return (
            "# 2HR Jobs MCP Server - Documentation\n\n"
            "## Available tools\n\n"
            "### Job search\n"
            "- search_jobs - main job search\n"
            "- find_remote_jobs - remote-only listings\n"
            "- find_jobs_in_city - jobs in a specific city\n"
            "- get_latest_jobs - newest listings\n\n"
            "### Salary analysis\n"
            "- get_salary_report - salary report for a technology\n"
            "- compare_salaries - compare two technologies\n"
            "- check_salary_fairness - assess offer vs market\n\n"
            "### Market analytics\n"
            "- get_top_technologies - technology ranking\n"
            "- compare_roles - compare two IT roles\n"
            "- get_market_trends - market trends\n"
            "- get_required_skills - skills for a role\n"
            "- get_top_employers - top hiring companies\n\n"
            "## Notes\n"
            "- Data from 2hr.pl Polish IT job board\n"
            "- Salaries in PLN gross/month\n"
            "- Cache TTL: jobs 5min, salary 60min, analytics 30min\n"
        )

    @mcp.resource("data://market/summary")
    async def get_market_summary() -> str:
        from api.client import JobsApiClient
        client = JobsApiClient()
        try:
            data = await client.get("/analytics/market-summary")
            summary = data.get("data", {})
            lines = [
                f"IT job market in Poland ({summary.get('date', 'today')}):",
                f"- Active jobs: {summary.get('active_jobs', 'N/A')}",
                f"- Remote jobs: {summary.get('remote_percentage', 'N/A')}%",
                f"- Top 3 technologies: {', '.join(summary.get('top_3_technologies', []))}",
                f"- Senior median salary: {summary.get('senior_median_salary', 'N/A')} PLN",
            ]
            return "\n".join(lines)
        except Exception:
            return "Could not fetch current market data."
