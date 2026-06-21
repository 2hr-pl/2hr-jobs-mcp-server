import time
import logging
from functools import wraps
from typing import Callable

logger = logging.getLogger(__name__)

call_counts: dict = {}
error_counts: dict = {}
latency_sums: dict = {}


def track_tool_call(tool_name: str):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.monotonic()
            call_counts[tool_name] = call_counts.get(tool_name, 0) + 1
            try:
                result = await func(*args, **kwargs)
                latency = time.monotonic() - start_time
                latency_sums[tool_name] = latency_sums.get(tool_name, 0) + latency
                if latency > 2.0:
                    logger.warning(f"Slow tool call {tool_name}: {latency:.2f}s")
                return result
            except Exception as e:
                error_counts[tool_name] = error_counts.get(tool_name, 0) + 1
                logger.error(f"Error in tool {tool_name}: {e}", exc_info=True)
                raise
        return wrapper
    return decorator


def get_stats() -> dict:
    stats = {}
    for tool in call_counts:
        calls = call_counts[tool]
        errors = error_counts.get(tool, 0)
        avg_latency = latency_sums.get(tool, 0) / calls if calls > 0 else 0
        stats[tool] = {
            "calls": calls,
            "errors": errors,
            "error_rate": f"{(errors / calls * 100):.1f}%" if calls > 0 else "0%",
            "avg_latency_ms": round(avg_latency * 1000, 1),
        }
    return stats
