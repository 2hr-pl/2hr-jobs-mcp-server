import re
import html
from typing import Optional

SUSPICIOUS_PATTERNS = [
    r'(drop|delete|truncate|alter|create|insert|update)\s+(table|database|schema)',
    r'union\s+select',
    r'<script',
    r'javascript:',
    r'data:text/html',
    r'\.\./\.\.',
    r'(exec|eval|system|passthru|shell_exec)',
]

COMPILED_SUSPICIOUS = [re.compile(p, re.IGNORECASE) for p in SUSPICIOUS_PATTERNS]

MAX_KEYWORD_LENGTH = 100
MAX_CITY_LENGTH = 50
MAX_ROLE_LENGTH = 80


def sanitize_search_input(value: str, max_length: int = MAX_KEYWORD_LENGTH) -> str:
    if not isinstance(value, str):
        raise ValueError("Input musi być stringiem")
    value = html.unescape(value).strip()
    if len(value) > max_length:
        value = value[:max_length]
    for pattern in COMPILED_SUSPICIOUS:
        if pattern.search(value):
            raise ValueError("Niedozwolone wyrażenie w zapytaniu")
    return value


def validate_salary(value: Optional[int], field_name: str = "salary") -> Optional[int]:
    if value is None:
        return None
    if not isinstance(value, int):
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValueError(f"{field_name} musi być liczbą całkowitą")
    if value < 1000:
        raise ValueError(f"{field_name} nie może być mniejsze niż 1000 PLN")
    if value > 200000:
        raise ValueError(f"{field_name} nie może być większe niż 200 000 PLN")
    return value


def validate_limit(value: int, max_limit: int = 50) -> int:
    if not isinstance(value, int):
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValueError("limit musi być liczbą całkowitą")
    return max(1, min(value, max_limit))


def validate_city(city: str) -> str:
    city = sanitize_search_input(city, MAX_CITY_LENGTH)
    if not re.match(r'^[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ\s\-]+$', city):
        raise ValueError("Nazwa miasta zawiera niedozwolone znaki")
    return city


class RateLimiter:

    def __init__(self, redis_client, max_requests: int = 100, window_seconds: int = 60):
        self.redis = redis_client
        self.max_requests = max_requests
        self.window = window_seconds

    async def is_allowed(self, identifier: str) -> tuple[bool, int]:
        key = f"rate_limit:{identifier}"
        try:
            client = await self.redis.get_client()
            current = await client.get(key)
            if current is None:
                await client.setex(key, self.window, 1)
                return True, self.max_requests - 1
            count = int(current)
            if count >= self.max_requests:
                return False, 0
            await client.incr(key)
            return True, self.max_requests - count - 1
        except Exception:
            return True, self.max_requests
