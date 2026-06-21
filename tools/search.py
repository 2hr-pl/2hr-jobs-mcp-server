from typing import Optional
from pydantic import BaseModel, Field, field_validator
from mcp.server.fastmcp import FastMCP
from api.client import JobsApiClient
from cache.redis_cache import get_cache
from security.validators import sanitize_search_input
import os

TTL_JOBS = int(os.getenv("CACHE_TTL_JOBS", "300"))
TTL_REMOTE = int(os.getenv("CACHE_TTL_REMOTE", "300"))
TTL_CITY = int(os.getenv("CACHE_TTL_CITY", "600"))

api_client = JobsApiClient()
cache = get_cache()


class JobSearchInput(BaseModel):
    keyword: str = Field(
        description="Technologia, rola lub umiejetnosc (np. 'Python', 'React Developer', 'DevOps')"
    )
    location: Optional[str] = Field(
        default=None,
        description="Miasto (np. 'Warszawa', 'Krakow') lub 'remote' dla pracy zdalnej",
    )
    salary_min: Optional[int] = Field(
        default=None, ge=1000, le=200000,
        description="Minimalne wynagrodzenie w PLN brutto/miesiac",
    )
    salary_max: Optional[int] = Field(
        default=None, ge=1000, le=200000,
        description="Maksymalne wynagrodzenie w PLN brutto/miesiac",
    )
    experience_level: Optional[str] = Field(
        default=None,
        description="Poziom: 'junior' (0-2 lata), 'mid' (2-5 lat), 'senior' (5+ lat), 'lead'",
    )
    employment_type: Optional[str] = Field(
        default=None,
        description="Forma zatrudnienia: 'b2b' (faktura), 'uop' (umowa o prace), 'zlecenie'",
    )
    limit: int = Field(default=10, ge=1, le=50, description="Liczba wynikow (domyslnie 10, max 50)")

    @field_validator('keyword')
    @classmethod
    def validate_keyword(cls, v: str) -> str:
        v = sanitize_search_input(v)
        if len(v) < 1:
            raise ValueError('Slowo kluczowe nie moze byc puste')
        return v

    @field_validator('experience_level')
    @classmethod
    def validate_experience(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {'junior', 'mid', 'senior', 'lead', 'principal'}
        if v.lower() not in allowed:
            raise ValueError(f'Poziom musi byc jednym z: {", ".join(allowed)}')
        return v.lower()

    @field_validator('employment_type')
    @classmethod
    def validate_employment(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {'b2b', 'uop', 'zlecenie', 'umowa_o_prace'}
        if v.lower() not in allowed:
            raise ValueError(f'Typ zatrudnienia musi byc jednym z: {", ".join(allowed)}')
        return v.lower()


def format_job_for_ai(job: dict) -> dict:
    salary_info = "nie podano"
    if job.get("salary_min") and job.get("salary_max"):
        salary_info = f"{job['salary_min']:,} - {job['salary_max']:,} PLN {job.get('employment_type', '').upper()}"
    elif job.get("salary_min"):
        salary_info = f"od {job['salary_min']:,} PLN"
    return {
        "id": job.get("id"),
        "tytul": job.get("title", ""),
        "firma": job.get("company", ""),
        "lokalizacja": job.get("location", ""),
        "zdalna": job.get("is_remote", False),
        "wynagrodzenie": salary_info,
        "poziom": job.get("experience_level", ""),
        "technologie": job.get("technologies", []),
        "data_dodania": job.get("created_at", ""),
        "url": job.get("url", ""),
        "opis_krotki": job.get("snippet", "")[:300] if job.get("snippet") else "",
    }


def register_search_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def search_jobs(params: JobSearchInput) -> dict:
        """
        Wyszukuje oferty pracy IT w Polsce.

        Uzyj gdy uzytkownik:
        - Pyta o dostepne oferty pracy dla konkretnej technologii
        - Chce znalezc prace w konkretnym miescie
        - Szuka ofert z okreslonym wynagrodzeniem
        - Pyta 'czy sa oferty dla X developera?'

        Przyklady: search_jobs(keyword='Python', location='Warszawa')
        search_jobs(keyword='React', salary_min=15000, experience_level='senior')
        """
        cache_params = params.model_dump()

        async def fetch():
            return await api_client.search_jobs(
                keyword=params.keyword,
                location=params.location,
                salary_min=params.salary_min,
                salary_max=params.salary_max,
                experience_level=params.experience_level,
                employment_type=params.employment_type,
                limit=params.limit,
            )

        result = await cache.get_or_set("jobs_search", cache_params, fetch, TTL_JOBS)
        jobs = result.get("jobs", [])

        return {
            "zapytanie": {
                "slowo_kluczowe": params.keyword,
                "lokalizacja": params.location or "wszystkie",
                "wynagrodzenie_min": params.salary_min,
                "wynagrodzenie_max": params.salary_max,
                "poziom": params.experience_level,
                "typ_zatrudnienia": params.employment_type,
            },
            "liczba_wynikow": result.get("total", len(jobs)),
            "oferty": [format_job_for_ai(j) for j in jobs],
            "czy_z_cache": result.get("_cached", False),
        }

    @mcp.tool()
    async def find_remote_jobs(
        keyword: Optional[str] = None,
        salary_min: Optional[int] = None,
        limit: int = 10,
    ) -> dict:
        """
        Wyszukuje wylacznie oferty pracy zdalnej (remote/home office).

        Uzyj gdy uzytkownik pyta o prace zdalna, home office,
        zdalne stanowiska dla konkretnej technologii.
        """
        if keyword:
            keyword = sanitize_search_input(keyword)

        cache_params = {"keyword": keyword, "salary_min": salary_min, "limit": limit}

        async def fetch():
            return await api_client.get_remote_jobs(keyword=keyword, limit=limit)

        result = await cache.get_or_set("remote_jobs", cache_params, fetch, TTL_REMOTE)
        jobs = result.get("jobs", [])

        if salary_min:
            jobs = [j for j in jobs if j.get("salary_min") and j["salary_min"] >= salary_min]

        return {
            "informacja": "Wszystkie ponizsze oferty umozliwiaja prace zdalna",
            "filtr_wynagrodzenia_min": salary_min,
            "liczba_wynikow": len(jobs),
            "oferty": [format_job_for_ai(j) for j in jobs],
        }

    @mcp.tool()
    async def find_jobs_in_city(
        city: str,
        keyword: Optional[str] = None,
        salary_min: Optional[int] = None,
        limit: int = 10,
    ) -> dict:
        """
        Wyszukuje oferty pracy w konkretnym polskim miescie.

        Uzyj gdy uzytkownik pyta o oferty w konkretnej lokalizacji,
        rynek pracy w danym miescie, porownanie miast.
        Obsluguje: Warszawa, Krakow, Wroclaw, Gdansk, Poznan, Lodz i inne.
        """
        from security.validators import validate_city
        city = validate_city(city)
        if keyword:
            keyword = sanitize_search_input(keyword)

        cache_params = {"city": city, "keyword": keyword, "salary_min": salary_min, "limit": limit}

        async def fetch():
            return await api_client.get_jobs_by_city(city=city, keyword=keyword, limit=limit)

        result = await cache.get_or_set("city_jobs", cache_params, fetch, TTL_CITY)
        jobs = result.get("jobs", [])

        if salary_min:
            jobs = [j for j in jobs if j.get("salary_min") and j["salary_min"] >= salary_min]

        return {
            "miasto": city,
            "technologia": keyword or "wszystkie",
            "liczba_ofert": len(jobs),
            "oferty": [format_job_for_ai(j) for j in jobs],
        }

    @mcp.tool()
    async def get_latest_jobs(limit: int = 20) -> dict:
        """
        Pobiera najnowsze oferty pracy IT dodane do portalu.

        Uzyj gdy uzytkownik pyta o najnowsze oferty,
        co nowego pojawilo sie na rynku, swieze oferty z ostatnich dni.
        """
        cache_params = {"limit": limit}

        async def fetch():
            return await api_client.get("/jobs/latest", {"limit": limit, "sort": "date_desc"})

        result = await cache.get_or_set("latest_jobs", cache_params, fetch, 120)
        jobs = result.get("jobs", [])

        return {
            "informacja": "Najnowsze oferty pracy IT w Polsce",
            "liczba": len(jobs),
            "oferty": [format_job_for_ai(j) for j in jobs],
        }
