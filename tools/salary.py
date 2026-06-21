import asyncio
from typing import Optional
from mcp.server.fastmcp import FastMCP
from api.client import JobsApiClient
from cache.redis_cache import get_cache
from security.validators import sanitize_search_input
import os

TTL_SALARY = int(os.getenv("CACHE_TTL_SALARY", "3600"))

api_client = JobsApiClient()
cache = get_cache()


def register_salary_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_salary_report(
        technology: str,
        experience_level: Optional[str] = None,
        employment_type: Optional[str] = None,
    ) -> dict:
        """
        Pobiera szczegolowy raport wynagrodzen dla technologii lub roli w Polsce.

        Uzyj gdy uzytkownik:
        - Pyta ile zarabia X developer
        - Chce wiedziec czy oferta jest uczciwa finansowo
        - Negocjuje wynagrodzenie i potrzebuje danych rynkowych
        - Porownuje zarobki w roznych technologiach

        Zwraca: mediane, percentyle (p25, p75, p90), rozklad B2B vs UoP,
        porownanie miast, trend (rosnace/stabilne/spadajace).
        """
        technology = sanitize_search_input(technology).lower()
        if experience_level:
            experience_level = experience_level.lower()

        cache_params = {
            "technology": technology,
            "experience_level": experience_level,
            "employment_type": employment_type,
        }

        async def fetch():
            return await api_client.get_salary_report(technology)

        result = await cache.get_or_set("salary_report", cache_params, fetch, TTL_SALARY)
        data = result.get("data", {})

        if experience_level and "by_level" in data:
            level_data = data["by_level"].get(experience_level, {})
            return {
                "technologia": technology,
                "poziom_doswiadczenia": experience_level,
                "mediana": level_data.get("median"),
                "percentyl_25": level_data.get("p25"),
                "percentyl_75": level_data.get("p75"),
                "percentyl_90": level_data.get("p90"),
                "liczba_ofert_w_analizie": level_data.get("sample_size"),
                "trend": level_data.get("trend", "stabilne"),
                "waluta": "PLN",
                "okres": "brutto/miesiac",
            }

        return {
            "technologia": technology,
            "wszystkie_poziomy": {
                "junior": data.get("junior", {}),
                "mid": data.get("mid", {}),
                "senior": data.get("senior", {}),
                "lead": data.get("lead", {}),
            },
            "wedlug_miasta": data.get("by_city", {}),
            "b2b_vs_uop": data.get("contract_comparison", {}),
            "trend_roczny": data.get("yearly_trend", "stabilne"),
            "liczba_ofert_w_analizie": data.get("sample_size", 0),
            "ostatnia_aktualizacja": data.get("updated_at", ""),
            "waluta": "PLN",
            "okres": "brutto/miesiac",
        }

    @mcp.tool()
    async def compare_salaries(
        technology_a: str,
        technology_b: str,
        experience_level: Optional[str] = None,
    ) -> dict:
        """
        Porownuje wynagrodzenia dwoch technologii lub rol w Polsce.

        Uzyj gdy uzytkownik pyta czy warto przejsc z X na Y ze wzgledu na zarobki,
        ktora technologia lepiej placi, czy zmiana specjalizacji ma sens finansowo.
        Wywoluje dane dla obu technologii rownolegle.
        """
        technology_a = sanitize_search_input(technology_a).lower()
        technology_b = sanitize_search_input(technology_b).lower()

        results_a, results_b = await asyncio.gather(
            cache.get_or_set(
                "salary_report",
                {"technology": technology_a, "experience_level": experience_level, "employment_type": None},
                lambda: api_client.get_salary_report(technology_a),
                TTL_SALARY,
            ),
            cache.get_or_set(
                "salary_report",
                {"technology": technology_b, "experience_level": experience_level, "employment_type": None},
                lambda: api_client.get_salary_report(technology_b),
                TTL_SALARY,
            ),
        )

        data_a = results_a.get("data", {})
        data_b = results_b.get("data", {})

        def get_median(data, level=None):
            if level and "by_level" in data:
                return data["by_level"].get(level, {}).get("median")
            return data.get("overall_median")

        median_a = get_median(data_a, experience_level)
        median_b = get_median(data_b, experience_level)

        different = None
        if median_a and median_b:
            diff = median_b - median_a
            diff_pct = (diff / median_a * 100) if median_a else 0
            different = {
                "roznica_PLN": diff,
                "roznica_procent": round(diff_pct, 1),
                "lepsza_technologia": technology_b if diff > 0 else technology_a,
            }

        return {
            "porownanie": f"{technology_a} vs {technology_b}",
            "poziom_doswiadczenia": experience_level or "wszystkie",
            technology_a: {"mediana": median_a, "trend": data_a.get("yearly_trend"), "liczba_ofert": data_a.get("sample_size")},
            technology_b: {"mediana": median_b, "trend": data_b.get("yearly_trend"), "liczba_ofert": data_b.get("sample_size")},
            "wynik_porownania": different,
            "uwaga": "Dane oparte na ofertach z portalu 2hr.pl z ostatnich 90 dni",
        }

    @mcp.tool()
    async def check_salary_fairness(
        technology: str,
        offered_salary: int,
        experience_level: str,
        employment_type: str = "b2b",
        location: Optional[str] = None,
    ) -> dict:
        """
        Ocenia czy zaproponowane wynagrodzenie jest uczciwe rynkowo.

        Uzyj gdy uzytkownik dostal oferte pracy i chce wiedziec czy pensja jest OK,
        negocjuje wynagrodzenie i potrzebuje argumentow,
        pyta 'czy 18 000 PLN B2B dla seniora React to dobra stawka?'

        Zwraca ocene (ponizej rynku / rynkowe / powyzej rynku) z uzasadnieniem.
        """
        technology = sanitize_search_input(technology).lower()
        experience_level = experience_level.lower()

        cache_params = {"technology": technology, "experience_level": experience_level, "employment_type": employment_type}

        async def fetch():
            return await api_client.get_salary_report(technology)

        result = await cache.get_or_set("salary_report", cache_params, fetch, TTL_SALARY)
        data = result.get("data", {})
        level_data = data.get("by_level", {}).get(experience_level, {})

        p25 = level_data.get("p25")
        median = level_data.get("median")
        p75 = level_data.get("p75")
        p90 = level_data.get("p90")

        assessment = "brak danych"
        recommendation = ""
        negotiation_space = None

        if median:
            if offered_salary < (p25 or median * 0.8):
                assessment = "znacznie ponizej rynku"
                recommendation = f"Rynek placi mediane {median:,} PLN. Mozesz negocjowac znacznie wyzej."
                negotiation_space = median - offered_salary
            elif offered_salary < median * 0.95:
                assessment = "ponizej rynku"
                recommendation = f"Mediana dla {technology} {experience_level} to {median:,} PLN. Masz przestrzen do negocjacji."
                negotiation_space = median - offered_salary
            elif offered_salary <= median * 1.05:
                assessment = "rynkowe"
                recommendation = "Wynagrodzenie jest zgodne z mediana rynkowa."
            elif offered_salary <= (p75 or median * 1.25):
                assessment = "powyzej mediany"
                recommendation = "Dobra oferta - powyzej mediany rynkowej."
            else:
                assessment = "bardzo powyzej rynku"
                recommendation = "Wyjatkowo dobra oferta - top 25% rynku."

        return {
            "technologia": technology,
            "poziom": experience_level,
            "typ_zatrudnienia": employment_type,
            "proponowane_wynagrodzenie": offered_salary,
            "ocena": assessment,
            "rekomendacja": recommendation,
            "przestrzen_negocjacyjna_PLN": negotiation_space,
            "dane_rynkowe": {"percentyl_25": p25, "mediana": median, "percentyl_75": p75, "percentyl_90": p90},
            "zrodlo": "Dane z portalu 2hr.pl, ostatnie 90 dni",
        }
