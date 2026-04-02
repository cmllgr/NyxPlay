from __future__ import annotations

from .actions import setup_logging
from .config import load_config
from .controller import run_listener


def run() -> None:
    cfg = load_config()
    setup_logging(cfg)
    run_listener(cfg)
