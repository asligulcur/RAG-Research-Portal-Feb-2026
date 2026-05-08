"""
LLM API Guard - Exponential backoff + bounded request rate for OpenAI calls.
Handles 429 rate-limit errors and throttles requests to avoid hitting limits.
"""

import os
import time
import logging
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Rate limit: min seconds between requests. Override via OPENAI_REQUEST_INTERVAL (default 1.0 = 1 req/sec)
MIN_REQUEST_INTERVAL = float(os.getenv("OPENAI_REQUEST_INTERVAL", "1.0"))
# Backoff: base delay, max delay, max retries
BACKOFF_BASE = 1.0
BACKOFF_MAX = 60.0
MAX_RETRIES = 5

_last_request_time = 0.0


def _rate_limit() -> None:
    """Ensure minimum interval between requests."""
    global _last_request_time
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        sleep_time = MIN_REQUEST_INTERVAL - elapsed
        logger.debug(f"Rate limit: sleeping {sleep_time:.2f}s")
        time.sleep(sleep_time)
    _last_request_time = time.monotonic()


def call_with_guard(fn: Callable[..., T], *args, **kwargs) -> T:
    """
    Execute an LLM API call with exponential backoff on 429 and rate throttling.
    """
    _rate_limit()
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            # Check for rate limit (429) - OpenAI raises RateLimitError or status_code 429
            is_rate_limit = (
                getattr(e, "status_code", None) == 429
                or "rate" in str(type(e).__name__).lower()
                or "429" in str(e).lower()
            )
            if is_rate_limit and attempt < MAX_RETRIES - 1:
                delay = min(BACKOFF_BASE * (2 ** attempt), BACKOFF_MAX)
                logger.warning(
                    f"Rate limit (429), retry {attempt + 1}/{MAX_RETRIES} in {delay:.1f}s"
                )
                time.sleep(delay)
                _rate_limit()
            else:
                raise
    raise last_exc
