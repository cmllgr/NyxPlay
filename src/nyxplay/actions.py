from __future__ import annotations

import logging
import os
import re
import subprocess
import threading
import time
from collections.abc import Callable
from typing import Any

from evdev import InputDevice, ecodes, ff

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


def find_sink_id_by_name(cfg: AppConfig, sink_name: str) -> int | None:
    result = run_command(cfg, ["wpctl", "status"], capture=True)
    if result is None or not result.stdout:
        logger.warning("Unable to read wpctl status")
        return None

    in_sinks_section = False

    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if "Sinks:" in line:
            in_sinks_section = True
            continue

        if in_sinks_section and line.startswith("Sources:"):
            break

        if not in_sinks_section:
            continue

        cleaned = line.lstrip("│* ").strip()

        match = re.match(r"^(\d+)\.\s+(.*)$", cleaned)
        if not match:
            continue

        sink_id = int(match.group(1))
        sink_label = match.group(2)

        if sink_name.lower() in sink_label.lower():
            return sink_id

    logger.warning("No sink matched name: %s", sink_name)
    return None


def set_default_sink_by_name(cfg: AppConfig, sink_name: str) -> bool:
    sink_id = find_sink_id_by_name(cfg, sink_name)
    if sink_id is None:
        logger.warning("Cannot set default sink, no match for: %s", sink_name)
        return False

    logger.info('Audio sink match "%s" -> id %s', sink_name, sink_id)
    run_command(cfg, ["wpctl", "set-default", str(sink_id)])
    return True


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


def start_rumble_async(device: InputDevice | None, cfg: AppConfig) -> None:
    if device is None or not cfg.rumble.enabled:
        return

    def _worker() -> None:
        try:
            capabilities = device.capabilities()
            ff_caps = capabilities.get(ecodes.EV_FF, [])
            if not ff_caps:
                return

            rumble = ff.Rumble(
                strong_magnitude=cfg.rumble.strong_magnitude,
                weak_magnitude=cfg.rumble.weak_magnitude,
            )
            effect = ff.Effect(
                ecodes.FF_RUMBLE,
                -1,
                0,
                ff.Trigger(0, 0),
                ff.Replay(cfg.rumble.duration_ms, 0),
                ff.EffectType(ff_rumble_effect=rumble),
            )

            effect_id = device.upload_effect(effect)
            device.write(ecodes.EV_FF, effect_id, 1)
            time.sleep(cfg.rumble.duration_ms / 1000.0)
            device.erase_effect(effect_id)
        except Exception as exc:
            logger.debug("Rumble unavailable: %s", exc)

    threading.Thread(target=_worker, daemon=True).start()
