import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tools.search import format_job_for_ai
from security.validators import sanitize_search_input, validate_salary


def test_sanitize_normal():
    assert sanitize_search_input("Python developer") == "Python developer"


def test_sanitize_sql_injection():
    with pytest.raises(ValueError, match="Niedozwolone wyrażenie"):
        sanitize_search_input("Python OR 1=1 UNION SELECT * FROM users")


def test_sanitize_too_long():
    result = sanitize_search_input("P" * 200)
    assert len(result) <= 100


def test_sanitize_path_traversal():
    with pytest.raises(ValueError):
        sanitize_search_input("../../etc/passwd")


def test_validate_salary_valid():
    assert validate_salary(15000) == 15000


def test_validate_salary_too_low():
    with pytest.raises(ValueError, match="1000 PLN"):
        validate_salary(100)


def test_validate_salary_too_high():
    with pytest.raises(ValueError, match="200 000 PLN"):
        validate_salary(500000)


def test_validate_salary_none():
    assert validate_salary(None) is None


def test_format_job_with_salary():
    job = {
        "id": 1,
        "title": "Senior Python Developer",
        "company": "Tech Corp",
        "location": "Warszawa",
        "is_remote": True,
        "salary_min": 20000,
        "salary_max": 30000,
        "employment_type": "b2b",
        "experience_level": "senior",
        "technologies": ["Python", "Django", "PostgreSQL"],
        "created_at": "2026-06-21",
        "url": "https://2hr.pl/oferta/123/",
        "snippet": "Szukamy seniora...",
    }
    result = format_job_for_ai(job)
    assert result["tytul"] == "Senior Python Developer"
    assert "20 000" in result["wynagrodzenie"]
    assert "B2B" in result["wynagrodzenie"]
    assert result["zdalna"] is True


def test_format_job_without_salary():
    job = {"id": 2, "title": "Junior Developer", "company": "Startup", "location": "Krakow", "is_remote": False}
    result = format_job_for_ai(job)
    assert result["wynagrodzenie"] == "nie podano"


@pytest.mark.asyncio
async def test_search_validates_keyword():
    from pydantic import ValidationError
    from tools.search import JobSearchInput
    with pytest.raises(ValidationError):
        JobSearchInput(keyword="DROP TABLE users --")
