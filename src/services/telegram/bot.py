"""Optional Telegram bot integration — disabled by default."""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, *args: Any, **kwargs: Any):
        pass

    async def start(self) -> None:
        logger.info("Telegram bot stub — not configured")

    async def stop(self) -> None:
        pass
