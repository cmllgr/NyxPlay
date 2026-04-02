from __future__ import annotations

import logging
import threading
import time

from evdev import InputDevice, ecodes, ff

from .actions import notify, run_command
from .config import AppConfig

logger = logging.getLogger("nyxplay")


def set_audio_tv(cfg: AppConfig) -> None:
    if cfg.audio.tv_sink_id is None:
        logger.warning("tv_sink_id is not configured")
        return

    logger.info("Audio -> TV (sink %s)", cfg.audio.tv_sink_id)
    run_command(cfg, ["wpctl", "set-default", str(cfg.audio.tv_sink_id)])


def set_audio_desk(cfg: AppConfig) -> None:
    if cfg.audio.desk_sink_id is None:
        logger.warning("desk_sink_id is not configured")
        return

    logger.info("Audio -> Desk (sink %s)", cfg.audio.desk_sink_id)
    run_command(cfg, ["wpctl", "set-default", str(cfg.audio.desk_sink_id)])


def _start_rumble_async(device: InputDevice | None, cfg: AppConfig) -> None:
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


def start_gamescope_session(cfg: AppConfig) -> None:
    run_command(
        cfg,
        [
            "systemd-run",
            "--user",
            "--collect",
            "--unit=nyxplay-gamescope",
            *cfg.launcher.gamescope_command,
        ],
        detach=True,
    )


def stop_gamescope_session(cfg: AppConfig) -> None:
    run_command(cfg, ["systemctl", "--user", "stop", "nyxplay-gamescope.service"])


def launch_gamescope_on_tv(cfg: AppConfig, device: InputDevice | None = None) -> None:
    logger.info("Launching TV gamescope session")
    notify(cfg, "TV on", "Gamescope")

    _start_rumble_async(device, cfg)

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

    _start_rumble_async(device, cfg)

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
