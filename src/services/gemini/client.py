import asyncio
import json
import logging
import re
from typing import Any, Optional

from src.config import GeminiSettings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Async wrapper around the Google Gemini API."""

    def __init__(self, settings: GeminiSettings):
        self.settings = settings
        self._client = None
        if settings.api_key:
            from google import genai

            self._client = genai.Client(api_key=settings.api_key)
            logger.info(f"Gemini client initialized (model={settings.model})")
        else:
            logger.warning("Gemini API key not configured — intelligence agents disabled")

    @property
    def is_available(self) -> bool:
        return bool(self._client and self.settings.enabled and self.settings.api_key)

    def _ensure_available(self) -> None:
        if not self.is_available:
            raise RuntimeError(
                "Gemini is not configured. Set GEMINI__API_KEY in your environment."
            )

    async def generate_json(
        self,
        prompt: str,
        *,
        system_instruction: Optional[str] = None,
    ) -> tuple[dict[str, Any], int]:
        """Generate structured JSON from Gemini. Returns (parsed_json, tokens_used)."""
        self._ensure_available()

        from google.genai import types

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        )
        if system_instruction:
            config.system_instruction = system_instruction

        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=self.settings.model,
            contents=prompt,
            config=config,
        )

        text = (response.text or "").strip()
        tokens = self._extract_tokens(response)
        return self._parse_json(text), tokens

    async def generate_text(
        self,
        prompt: str,
        *,
        system_instruction: Optional[str] = None,
    ) -> tuple[str, int]:
        self._ensure_available()

        from google.genai import types

        config = types.GenerateContentConfig(temperature=0.2)
        if system_instruction:
            config.system_instruction = system_instruction

        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=self.settings.model,
            contents=prompt,
            config=config,
        )
        return (response.text or "").strip(), self._extract_tokens(response)

    @staticmethod
    def _extract_tokens(response: Any) -> int:
        usage = getattr(response, "usage_metadata", None)
        if not usage:
            return 0
        return int(
            getattr(usage, "total_token_count", 0)
            or getattr(usage, "prompt_token_count", 0) + getattr(usage, "candidates_token_count", 0)
        )

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError(f"Gemini returned non-JSON response: {text[:200]}")
