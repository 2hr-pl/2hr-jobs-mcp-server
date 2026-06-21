from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:

    @mcp.prompt()
    def job_search_assistant() -> str:
        return (
            "I am an IT job search assistant for Poland, powered by 2hr.pl data.\n"
            "I have access to live job listings, salary data, and market analytics.\n\n"
            "Tell me what you are looking for:\n"
            "- Which technology or role interests you?\n"
            "- Which city do you prefer (or remote)?\n"
            "- What experience level do you have?\n"
            "- What salary range are you targeting?\n\n"
            "I can also assess whether a specific offer is fair vs market rates,\n"
            "or compare salaries for different technologies."
        )

    @mcp.prompt()
    def salary_negotiation_assistant() -> str:
        return (
            "I help with salary negotiations in IT, using live market data from 2hr.pl.\n\n"
            "To assess your situation, I need:\n"
            "1. Which technology/role do you work in?\n"
            "2. How many years of experience do you have?\n"
            "3. What salary have you been offered?\n"
            "4. Is it B2B (invoice) or employment contract (UoP)?\n"
            "5. Which city (or remote)?\n\n"
            "Based on this I will check where the offer stands vs market\n"
            "and how to argue for a higher salary."
        )
