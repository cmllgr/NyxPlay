from __future__ import annotations

import json
import logging
import time

from .actions import run_command
from .config import AppConfig

logger = logging.getLogger("nyxplay")


def get_clients(cfg: AppConfig) -> list[dict]:
    result = run_command(cfg, ["hyprctl", "clients", "-j"], capture=True)
    if result is None or not result.stdout:
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.warning("Failed to parse hyprctl clients -j output")
        return []

    if not isinstance(data, list):
        return []

    return data


def find_client_address_by_class(
    cfg: AppConfig,
    class_name: str,
) -> str | None:
    for client in get_clients(cfg):
        client_class = str(client.get("class", ""))
        if client_class == class_name:
            return str(client.get("address", ""))

    return None


def wait_for_client_address(
    cfg: AppConfig,
    class_name: str,
    timeout_seconds: float = 5.0,
    poll_interval: float = 0.1,
) -> str | None:
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        address = find_client_address_by_class(cfg, class_name)
        if address:
            return address
        time.sleep(poll_interval)

    return None


def move_client_to_workspace(
    cfg: AppConfig,
    address: str,
    workspace: int,
) -> None:
    run_command(
        cfg,
        [
            "hyprctl",
            "dispatch",
            "movetoworkspacesilent",
            f"{workspace},address:{address}",
        ],
    )
