from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from evdev import ecodes

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "default" / "config.toml"


@dataclass(slots=True)
class DeviceConfig:
    name: str
    uniq: str | None


@dataclass(slots=True)
class TimingConfig:
    combo_cooldown_seconds: float
    volume_cooldown_seconds: float
    poweroff_hold_seconds: float
    poweroff_cooldown_seconds: float
    hold_action_seconds: float
    trigger_press_threshold: int
    trigger_release_threshold: int
    loop_sleep_seconds: float
    device_poll_seconds: float


@dataclass(slots=True)
class LoggingConfig:
    level: str
    debug_commands: bool


@dataclass(slots=True)
class NotificationConfig:
    enabled: bool
    timeout_ms: int
    title: str


@dataclass(slots=True)
class RumbleConfig:
    enabled: bool
    strong_magnitude: int
    weak_magnitude: int
    duration_ms: int


@dataclass(slots=True)
class AudioConfig:
    tv_sink_id: int | None
    desk_sink_id: int | None
    volume_step_percent: int
    max_volume: float


@dataclass(slots=True)
class LauncherConfig:
    tv_monitor: str
    tv_monitor_conf: str
    gamescope_command: list[str]
    gamescope_start_delay_seconds: float
    gamescope_stop_delay_seconds: float


@dataclass(slots=True)
class BindingConfig:
    primary_mod_1: int
    primary_mod_2: int
    action_gamescope_on: int
    action_gamescope_off: int
    action_audio_toggle: int
    action_mic_toggle: int
    dpad_vertical_axis: int
    dpad_up_value: int
    dpad_down_value: int
    power_mod_analog_1: int
    power_mod_analog_2: int


@dataclass(slots=True)
class AppConfig:
    device: DeviceConfig
    timing: TimingConfig
    logging: LoggingConfig
    notifications: NotificationConfig
    rumble: RumbleConfig
    audio: AudioConfig
    launcher: LauncherConfig
    bindings: BindingConfig


def _ecode(name: str) -> int:
    value = getattr(ecodes, name, None)
    if value is None:
        raise ValueError(f"Unknown evdev code: {name}")
    return value


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or DEFAULT_CONFIG_PATH

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("rb") as f:
        data = tomllib.load(f)

    device = data["device"]
    timing = data["timing"]
    logging_cfg = data["logging"]
    notifications = data["notifications"]
    rumble = data["rumble"]
    audio = data["audio"]
    launcher = data["launcher"]
    bindings = data["bindings"]

    return AppConfig(
        device=DeviceConfig(
            name=str(device["name"]),
            uniq=str(device["uniq"]) if device.get("uniq") else None,
        ),
        timing=TimingConfig(
            combo_cooldown_seconds=float(timing["combo_cooldown_seconds"]),
            volume_cooldown_seconds=float(timing["volume_cooldown_seconds"]),
            poweroff_hold_seconds=float(timing["poweroff_hold_seconds"]),
            poweroff_cooldown_seconds=float(timing["poweroff_cooldown_seconds"]),
            hold_action_seconds=float(timing["hold_action_seconds"]),
            trigger_press_threshold=int(timing["trigger_press_threshold"]),
            trigger_release_threshold=int(timing["trigger_release_threshold"]),
            loop_sleep_seconds=float(timing["loop_sleep_seconds"]),
            device_poll_seconds=float(timing["device_poll_seconds"]),
        ),
        logging=LoggingConfig(
            level=str(logging_cfg["level"]).upper(),
            debug_commands=bool(logging_cfg["debug_commands"]),
        ),
        notifications=NotificationConfig(
            enabled=bool(notifications["enabled"]),
            timeout_ms=int(notifications["timeout_ms"]),
            title=str(notifications["title"]),
        ),
        rumble=RumbleConfig(
            enabled=bool(rumble["enabled"]),
            strong_magnitude=int(rumble["strong_magnitude"]),
            weak_magnitude=int(rumble["weak_magnitude"]),
            duration_ms=int(rumble["duration_ms"]),
        ),
        audio=AudioConfig(
            tv_sink_id=(int(audio["tv_sink_id"]) if audio.get("tv_sink_id") is not None else None),
            desk_sink_id=(
                int(audio["desk_sink_id"]) if audio.get("desk_sink_id") is not None else None
            ),
            volume_step_percent=int(audio["volume_step_percent"]),
            max_volume=float(audio["max_volume"]),
        ),
        launcher=LauncherConfig(
            tv_monitor=str(launcher["tv_monitor"]),
            tv_monitor_conf=str(launcher["tv_monitor_conf"]),
            gamescope_command=[str(x) for x in launcher["gamescope_command"]],
            gamescope_start_delay_seconds=float(launcher["gamescope_start_delay_seconds"]),
            gamescope_stop_delay_seconds=float(launcher["gamescope_stop_delay_seconds"]),
        ),
        bindings=BindingConfig(
            primary_mod_1=_ecode(bindings["primary_mod_1"]),
            primary_mod_2=_ecode(bindings["primary_mod_2"]),
            action_gamescope_on=_ecode(bindings["action_gamescope_on"]),
            action_gamescope_off=_ecode(bindings["action_gamescope_off"]),
            action_audio_toggle=_ecode(bindings["action_audio_toggle"]),
            action_mic_toggle=_ecode(bindings["action_mic_toggle"]),
            dpad_vertical_axis=_ecode(bindings["dpad_vertical_axis"]),
            dpad_up_value=int(bindings["dpad_up_value"]),
            dpad_down_value=int(bindings["dpad_down_value"]),
            power_mod_analog_1=_ecode(bindings["power_mod_analog_1"]),
            power_mod_analog_2=_ecode(bindings["power_mod_analog_2"]),
        ),
    )
