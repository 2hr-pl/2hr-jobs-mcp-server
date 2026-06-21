import httpx
import os
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()


class JobsApiClient:

    def __init__(self):
        self.base_url = os.getenv("JOBS_API_URL", "https://api.2hr.pl/v1")
        self.api_key = os.getenv("JOBS_API_KEY", "")
        self.timeout = float(os.getenv("API_TIMEOUT", "10.0"))

    def _get_headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "2HR-MCP-Server/1.0",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def get(self, endpoint: str, params: Optional[dict] = None) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/{endpoint.lstrip('/')}",
                params=params,
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()

    async def search_jobs(
        self,
        keyword: str,
        location: Optional[str] = None,
        salary_min: Optional[int] = None,
        salary_max: Optional[int] = None,
        experience_level: Optional[str] = None,
        employment_type: Optional[str] = None,
        limit: int = 10,
    ) -> dict:
        params = {"q": keyword, "limit": limit}
        if location:
            params["location"] = location
        if salary_min:
            params["salary_min"] = salary_min
        if salary_max:
            params["salary_max"] = salary_max
        if experience_level:
            params["level"] = experience_level
        if employment_type:
            params["type"] = employment_type
        return await self.get("/jobs/search", params)

    async def get_salary_report(self, technology: str) -> dict:
        return await self.get("/salary/report", {"technology": technology})

    async def get_top_technologies(self, limit: int = 20) -> dict:
        return await self.get("/analytics/top-technologies", {"limit": limit})

    async def compare_roles(self, role_a: str, role_b: str) -> dict:
        return await self.get("/analytics/compare", {"role_a": role_a, "role_b": role_b})

    async def get_market_trends(self, period: str = "3m") -> dict:
        return await self.get("/analytics/trends", {"period": period})

    async def get_remote_jobs(self, keyword: Optional[str] = None, limit: int = 10) -> dict:
        params = {"remote": "true", "limit": limit}
        if keyword:
            params["q"] = keyword
        return await self.get("/jobs/search", params)

    async def get_jobs_by_city(self, city: str, keyword: Optional[str] = None, limit: int = 10) -> dict:
        params = {"location": city, "limit": limit}
        if keyword:
            params["q"] = keyword
        return await self.get("/jobs/search", params)
