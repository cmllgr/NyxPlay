from __future__ import annotations

import logging

from .actions import setup_logging
from .config import load_config
from .controller import run_listener

logger = logging.getLogger("nyxplay")


def run() -> None:
    cfg = load_config()
    setup_logging(cfg)

    try:
        run_listener(cfg)
    except KeyboardInterrupt:
        logger.info("Stopping nyxplay")
