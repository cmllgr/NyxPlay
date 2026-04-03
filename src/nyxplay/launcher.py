from __future__ import annotations

import logging
import shlex
import time

from evdev import InputDevice

from .actions import notify, run_command, set_default_sink_by_name, start_rumble_async
from .config import AppConfig
from .hyprland import move_client_to_workspace, wait_for_client_address

logger = logging.getLogger("nyxplay")


def set_audio_tv(cfg: AppConfig) -> None:
    if cfg.audio.tv_sink_name is None:
        logger.warning("tv_sink_name is not configured")
        return

    set_default_sink_by_name(cfg, cfg.audio.tv_sink_name)


def set_audio_desk(cfg: AppConfig) -> None:
    if cfg.audio.desk_sink_name is None:
        logger.warning("desk_sink_name is not configured")
        return

    set_default_sink_by_name(cfg, cfg.audio.desk_sink_name)


def start_gamescope_session(cfg: AppConfig) -> None:
    command = " ".join(shlex.quote(arg) for arg in cfg.launcher.gamescope_command)

    logger.info("Starting gamescope on workspace %s", cfg.launcher.tv_workspace)
    run_command(
        cfg,
        [
            "hyprctl",
            "dispatch",
            "exec",
            command,
        ],
    )

    address = wait_for_client_address(cfg, "gamescope", timeout_seconds=5.0)
    if address is None:
        logger.warning("Gamescope window not found after launch")
        return

    logger.info("Gamescope client found: %s", address)
    move_client_to_workspace(cfg, address, cfg.launcher.tv_workspace)


def stop_gamescope_session(cfg: AppConfig) -> None:
    run_command(cfg, ["pkill", "-x", "gamescope"], check=False)
    run_command(cfg, ["pkill", "-x", "gamescopereaper"], check=False)


def launch_gamescope_on_tv(cfg: AppConfig, device: InputDevice | None = None) -> None:
    logger.info("Launching TV gamescope session")
    notify(cfg, "TV on", "Gamescope")

    start_rumble_async(device, cfg)

    run_command(
        cfg,
        [
            "hyprctl",
            "keyword",
            "monitor",
            cfg.launcher.tv_monitor_conf,
        ],
    )

    set_audio_tv(cfg)
    start_gamescope_session(cfg)

    if cfg.launcher.gamescope_start_delay_seconds > 0:
        time.sleep(cfg.launcher.gamescope_start_delay_seconds)


def stop_gamescope_on_tv(cfg: AppConfig, device: InputDevice | None = None) -> None:
    logger.info("Stopping TV gamescope session")
    notify(cfg, "TV off", "Gamescope")

    start_rumble_async(device, cfg)

    stop_gamescope_session(cfg)

    if cfg.launcher.gamescope_stop_delay_seconds > 0:
        time.sleep(cfg.launcher.gamescope_stop_delay_seconds)

    run_command(
        cfg,
        [
            "hyprctl",
            "keyword",
            "monitor",
            f"{cfg.launcher.tv_monitor},disable",
        ],
    )

    set_audio_desk(cfg)
