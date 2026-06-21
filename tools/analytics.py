import asyncio
from typing import Optional
from mcp.server.fastmcp import FastMCP
from api.client import JobsApiClient
from cache.redis_cache import get_cache
from security.validators import sanitize_search_input
import os

TTL_ANALYTICS = int(os.getenv("CACHE_TTL_ANALYTICS", "1800"))
TTL_TRENDS = int(os.getenv("CACHE_TTL_TRENDS", "3600"))

api_client = JobsApiClient()
cache = get_cache()


def register_analytics_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_top_technologies(
        category: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        """
        Pobiera ranking najpopularniejszych technologii IT w Polsce wedlug liczby ofert.

        Uzyj gdy uzytkownik pyta ktore technologie sa najczesciej wymagane,
        co warto sie nauczyc dla lepszej zatrudnialnosci,
        'jakie technologie sa teraz na topie w Polsce?'

        Kategorie: 'backend', 'frontend', 'mobile', 'devops', 'data', 'security'
        """
        cache_params = {"category": category, "limit": limit}

        async def fetch():
            params = {"limit": limit}
            if category:
                params["category"] = category
            return await api_client.get("/analytics/top-technologies", params)

        result = await cache.get_or_set("top_technologies", cache_params, fetch, TTL_ANALYTICS)
        technologies = result.get("technologies", [])

        return {
            "informacja": f"Top {limit} technologii wedlug liczby aktywnych ofert pracy",
            "kategoria": category or "wszystkie",
            "ranking": [
                {
                    "pozycja": idx + 1,
                    "technologia": tech.get("name"),
                    "liczba_ofert": tech.get("job_count"),
                    "zmiana_miesieczna": tech.get("monthly_change"),
                    "trend": tech.get("trend", "stabilny"),
                    "mediana_wynagrodzenia": tech.get("median_salary"),
                }
                for idx, tech in enumerate(technologies)
            ],
            "data_analizy": result.get("generated_at"),
        }

    @mcp.tool()
    async def compare_roles(role_a: str, role_b: str) -> dict:
        """
        Porownuje dwie role zawodowe IT pod katem ofert, wynagrodzen i wymagan.

        Uzyj gdy uzytkownik zastanawia sie miedzy dwiema sciezkami kariery,
        pyta 'Backend vs Frontend - co wybrac?', DevOps vs SRE,
        Data Scientist vs Data Engineer.
        """
        role_a = sanitize_search_input(role_a)
        role_b = sanitize_search_input(role_b)

        result_a, result_b = await asyncio.gather(
            cache.get_or_set("role_analysis", {"role": role_a}, lambda: api_client.get("/analytics/role", {"role": role_a}), TTL_ANALYTICS),
            cache.get_or_set("role_analysis", {"role": role_b}, lambda: api_client.get("/analytics/role", {"role": role_b}), TTL_ANALYTICS),
        )

        def extract_role_data(result: dict, role_name: str) -> dict:
            data = result.get("data", {})
            return {
                "rola": role_name,
                "liczba_aktywnych_ofert": data.get("active_jobs", 0),
                "mediana_wynagrodzenia_senior": data.get("senior_median_salary"),
                "wymagane_technologie_top5": data.get("top_skills", [])[:5],
                "poziom_trudnosci_wejscia": data.get("entry_difficulty", ""),
                "dostepnosc_pracy_zdalnej": data.get("remote_percentage", 0),
                "trend_ofert": data.get("jobs_trend", ""),
                "czas_do_pierwszej_pracy": data.get("time_to_hire_days"),
            }

        data_a = extract_role_data(result_a, role_a)
        data_b = extract_role_data(result_b, role_b)

        winner_salary = None
        winner_jobs = None
        if data_a.get("mediana_wynagrodzenia_senior") and data_b.get("mediana_wynagrodzenia_senior"):
            winner_salary = role_a if data_a["mediana_wynagrodzenia_senior"] > data_b["mediana_wynagrodzenia_senior"] else role_b
        if data_a.get("liczba_aktywnych_ofert") and data_b.get("liczba_aktywnych_ofert"):
            winner_jobs = role_a if data_a["liczba_aktywnych_ofert"] > data_b["liczba_aktywnych_ofert"] else role_b

        return {
            "porownanie": f"{role_a} vs {role_b}",
            role_a: data_a,
            role_b: data_b,
            "podsumowanie": {
                "lepsze_wynagrodzenie": winner_salary,
                "wiecej_ofert": winner_jobs,
                "uwaga": "Ostateczny wybor zalezy od Twoich zainteresowan i umiejetnosci",
            },
        }

    @mcp.tool()
    async def get_market_trends(
        period: str = "3m",
        technology: Optional[str] = None,
    ) -> dict:
        """
        Pobiera trendy rynku pracy IT w Polsce za wybrany okres.

        Uzyj gdy uzytkownik pyta jak zmienia sie rynek pracy IT,
        czy technologia X rosnie czy maleje, o sezonowosc ofert,
        'czy warto uczyc sie X - czy to przyszlosciowe?'

        Okresy: '1m', '3m', '6m', '1y'
        """
        valid_periods = {'1m', '3m', '6m', '1y'}
        if period not in valid_periods:
            period = "3m"
        if technology:
            technology = sanitize_search_input(technology).lower()

        cache_params = {"period": period, "technology": technology}

        async def fetch():
            params = {"period": period}
            if technology:
                params["technology"] = technology
            return await api_client.get("/analytics/trends", params)

        result = await cache.get_or_set("market_trends", cache_params, fetch, TTL_TRENDS)
        data = result.get("data", {})

        return {
            "okres_analizy": period,
            "technologia": technology or "caly rynek IT",
            "ogolne_trendy": {
                "zmiana_liczby_ofert": data.get("job_count_change"),
                "zmiana_procentowa": data.get("job_count_change_pct"),
                "zmiana_wynagrodzen": data.get("salary_change"),
                "dominujace_kontrakty": data.get("dominant_contract_type"),
            },
            "rosnace_technologie": data.get("growing_technologies", []),
            "malejace_technologie": data.get("declining_technologies", []),
            "nowe_wymagania": data.get("emerging_skills", []),
            "sezonowosc": data.get("seasonality_note"),
            "prognoza_nastepne_3m": data.get("forecast_3m"),
        }

    @mcp.tool()
    async def get_required_skills(
        role: str,
        experience_level: Optional[str] = None,
    ) -> dict:
        """
        Pobiera liste umiejetnosci najczesciej wymaganych dla danej roli.

        Uzyj gdy uzytkownik pyta czego sie nauczyc zeby dostac prace jako X,
        jakie skille sa potrzebne, przygotowuje CV.
        Dzieli umiejetnosci na: must-have, nice-to-have, differentiators.
        """
        role = sanitize_search_input(role)
        if experience_level:
            experience_level = experience_level.lower()

        cache_params = {"role": role, "level": experience_level}

        async def fetch():
            params = {"role": role}
            if experience_level:
                params["level"] = experience_level
            return await api_client.get("/analytics/required-skills", params)

        result = await cache.get_or_set("required_skills", cache_params, fetch, TTL_ANALYTICS)
        data = result.get("data", {})

        return {
            "rola": role,
            "poziom": experience_level or "wszystkie",
            "obowiazkowe_w_ponad_70_proc_ofert": data.get("must_have", []),
            "mile_widziane_30_70_proc": data.get("nice_to_have", []),
            "wyroznajace_ponizej_30_proc": data.get("differentiators", []),
            "certyfikaty_ktore_pomagaja": data.get("helpful_certifications", []),
            "miekkie_umiejetnosci": data.get("soft_skills", []),
            "liczba_przeanalizowanych_ofert": data.get("analyzed_jobs_count"),
        }

    @mcp.tool()
    async def get_top_employers(
        technology: Optional[str] = None,
        city: Optional[str] = None,
        limit: int = 15,
    ) -> dict:
        """
        Pobiera liste pracodawcow z najwieksza liczba aktywnych ofert pracy IT.

        Uzyj gdy uzytkownik chce wiedziec kto duzo rekrutuje,
        pyta o pracodawcow w danej technologii lub miescie,
        'kto zatrudnia Python developerow w Krakowie?'
        """
        if technology:
            technology = sanitize_search_input(technology).lower()
        if city:
            city = sanitize_search_input(city)

        cache_params = {"technology": technology, "city": city, "limit": limit}

        async def fetch():
            params = {"limit": limit}
            if technology:
                params["technology"] = technology
            if city:
                params["city"] = city
            return await api_client.get("/analytics/top-employers", params)

        result = await cache.get_or_set("top_employers", cache_params, fetch, TTL_ANALYTICS)
        employers = result.get("employers", [])

        return {
            "filtr_technologia": technology or "wszystkie",
            "filtr_miasto": city or "wszystkie",
            "pracodawcy": [
                {
                    "firma": emp.get("company_name"),
                    "liczba_aktywnych_ofert": emp.get("active_jobs"),
                    "branza": emp.get("industry"),
                    "glowna_lokalizacja": emp.get("main_location"),
                    "praca_zdalna": emp.get("offers_remote", False),
                    "technologie_szukane": emp.get("top_technologies", [])[:3],
                }
                for emp in employers
            ],
        }
