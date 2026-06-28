"""No-op virus scanner stub for development."""

import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


class VirusScannerService:
    """Stub virus scanner — always passes unless explicitly disabled."""

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        logger.info(f"Virus scanner initialized (enabled={enabled})")

    async def scan_file(self, file_path: Path) -> Tuple[bool, str]:
        if not self.enabled:
            return True, ""
        logger.warning("Virus scanning enabled but no scanner configured — passing by default")
        return True, ""
