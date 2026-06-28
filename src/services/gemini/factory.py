from functools import lru_cache

from src.config import get_settings

from .client import GeminiClient


@lru_cache(maxsize=1)
def make_gemini_client() -> GeminiClient:
    settings = get_settings()
    return GeminiClient(settings.gemini)
