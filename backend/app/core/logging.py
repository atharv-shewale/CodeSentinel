"""
CodeSentinel Backend: Logging Configuration.
"""

import logging
import sys
from .config import settings


def setup_logging() -> None:
    """Configure structured console logging for the application."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


logger = logging.getLogger("codesentinel")
