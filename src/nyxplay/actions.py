from __future__ import annotations

import logging
import os
import subprocess
import time
from collections.abc import Callable
from typing import Any

from .config import AppConfig

logger = logging.getLogger("nyxplay")


def setup_logging(cfg: AppConfig) -> None:
    level_name = cfg.logging.level.upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="[nyxplay] %(levelname)s: %(message)s",
    )


def _runtime_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    return env


def run_command(
    cfg: AppConfig,
    cmd: list[str],
    *,
    check: bool = False,
    capture: bool = False,
    detach: bool = False,
) -> subprocess.CompletedProcess[str] | None:
    if cfg.logging.debug_commands:
        logger.debug("CMD: %s", " ".join(cmd))

    env = _runtime_env()

    if detach:
        subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return None

    if capture:
        return subprocess.run(
            cmd,
            env=env,
            check=check,
            text=True,
            capture_output=True,
        )

    return subprocess.run(
        cmd,
        env=env,
        check=check,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def command_ok(cfg: AppConfig, cmd: list[str]) -> bool:
    result = run_command(cfg, cmd, check=False, capture=False)
    return result is not None and result.returncode == 0


def notify(cfg: AppConfig, message: str, title: str | None = None) -> None:
    if not cfg.notifications.enabled:
        return

    run_command(
        cfg,
        [
            "notify-send",
            "-h",
            "int:transient:1",
            "-t",
            str(cfg.notifications.timeout_ms),
            title or cfg.notifications.title,
            message,
        ],
    )


def get_wpctl_muted(cfg: AppConfig, target: str) -> bool:
    result = run_command(cfg, ["wpctl", "get-volume", target], capture=True)
    if result is None:
        return False

    return "[MUTED]" in (result.stdout or "")


def retry(
    attempts: int,
    delay_seconds: float,
    fn: Callable[..., bool],
    *args: Any,
    **kwargs: Any,
) -> bool:
    for attempt in range(1, attempts + 1):
        if fn(*args, **kwargs):
            return True

        if attempt < attempts:
            time.sleep(delay_seconds)

    return False


def toggle_audio(cfg: AppConfig) -> bool:
    run_command(cfg, ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"])
    return get_wpctl_muted(cfg, "@DEFAULT_AUDIO_SINK@")


def toggle_mic(cfg: AppConfig) -> bool:
    run_command(cfg, ["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "toggle"])
    return get_wpctl_muted(cfg, "@DEFAULT_AUDIO_SOURCE@")


def volume_up(cfg: AppConfig) -> None:
    step = f"{cfg.audio.volume_step_percent}%+"
    max_volume = str(cfg.audio.max_volume)

    run_command(
        cfg,
        ["wpctl", "set-volume", "-l", max_volume, "@DEFAULT_AUDIO_SINK@", step],
    )


def volume_down(cfg: AppConfig) -> None:
    step = f"{cfg.audio.volume_step_percent}%-"

    run_command(
        cfg,
        ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", step],
    )


def poweroff(cfg: AppConfig) -> None:
    run_command(cfg, ["systemctl", "poweroff"], detach=True)
