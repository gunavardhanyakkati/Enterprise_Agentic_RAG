import logging
from typing import Any, Optional

from .bot import TelegramBot

logger = logging.getLogger(__name__)


def make_telegram_service(*args: Any, **kwargs: Any) -> Optional[TelegramBot]:
    from src.config import get_settings

    settings = get_settings()
    if not settings.telegram.enabled or not settings.telegram.bot_token:
        return None
    logger.info("Telegram enabled but stub implementation — skipping bot startup")
    return None
