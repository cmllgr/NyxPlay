from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from evdev import InputDevice

from .actions import notify, poweroff, toggle_audio, toggle_mic, volume_down, volume_up
from .config import AppConfig
from .launcher import launch_gamescope_on_tv, stop_gamescope_on_tv

logger = logging.getLogger("nyxplay")


def now() -> float:
    return time.monotonic()


@dataclass
class RuntimeState:
    pressed: dict[str, bool] = field(
        default_factory=lambda: {
            "mod1": False,
            "mod2": False,
            "pow1": False,
            "pow2": False,
            "dpad_up": False,
            "dpad_down": False,
        }
    )
    last_triggered: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    held_actions_started_at: dict[str, float | None] = field(
        default_factory=lambda: {
            "gamescope_on": None,
            "gamescope_off": None,
            "audio_toggle": None,
            "mic_toggle": None,
        }
    )
    held_actions_fired: dict[str, bool] = field(
        default_factory=lambda: {
            "gamescope_on": False,
            "gamescope_off": False,
            "audio_toggle": False,
            "mic_toggle": False,
        }
    )
    poweroff_started_at: float | None = None

    def reset(self) -> None:
        for key in self.pressed:
            self.pressed[key] = False

        self.last_triggered.clear()
        self.poweroff_started_at = None

        for key in self.held_actions_started_at:
            self.held_actions_started_at[key] = None

        for key in self.held_actions_fired:
            self.held_actions_fired[key] = False

    def reset_held_action(self, name: str) -> None:
        self.held_actions_started_at[name] = None
        self.held_actions_fired[name] = False


def can_trigger(state: RuntimeState, name: str, cooldown: float) -> bool:
    return (now() - state.last_triggered[name]) >= cooldown


def mark_triggered(state: RuntimeState, name: str) -> None:
    state.last_triggered[name] = now()


def modifiers_active(state: RuntimeState) -> bool:
    return state.pressed["mod1"] and state.pressed["mod2"]


def power_modifiers_active(state: RuntimeState) -> bool:
    return state.pressed["pow1"] and state.pressed["pow2"]


def start_hold_action(state: RuntimeState, name: str) -> None:
    if state.held_actions_started_at[name] is None:
        state.held_actions_started_at[name] = now()
        state.held_actions_fired[name] = False


def stop_hold_action(state: RuntimeState, name: str) -> None:
    state.reset_held_action(name)


def maybe_fire_hold_action(
    cfg: AppConfig,
    state: RuntimeState,
    name: str,
    hold_seconds: float,
    callback: Callable[[], None],
) -> None:
    started_at = state.held_actions_started_at[name]
    if started_at is None:
        return

    if state.held_actions_fired[name]:
        return

    if now() - started_at < hold_seconds:
        return

    callback()
    state.held_actions_fired[name] = True


def update_analog_state(state: RuntimeState, name: str, value: int, cfg: AppConfig) -> None:
    if value >= cfg.timing.trigger_press_threshold:
        state.pressed[name] = True
    elif value <= cfg.timing.trigger_release_threshold:
        state.pressed[name] = False


def trigger_gamescope_on(cfg: AppConfig, state: RuntimeState, device: InputDevice) -> None:
    if not can_trigger(state, "gamescope_on", cfg.timing.combo_cooldown_seconds):
        return

    mark_triggered(state, "gamescope_on")
    launch_gamescope_on_tv(cfg, device)


def trigger_gamescope_off(cfg: AppConfig, state: RuntimeState, device: InputDevice) -> None:
    if not can_trigger(state, "gamescope_off", cfg.timing.combo_cooldown_seconds):
        return

    mark_triggered(state, "gamescope_off")
    stop_gamescope_on_tv(cfg, device)


def trigger_audio_toggle(cfg: AppConfig, state: RuntimeState) -> None:
    if not can_trigger(state, "audio_toggle", cfg.timing.combo_cooldown_seconds):
        return

    mark_triggered(state, "audio_toggle")
    muted = toggle_audio(cfg)
    logger.info("Audio off" if muted else "Audio on")
    notify(cfg, "Audio off" if muted else "Audio on")


def trigger_mic_toggle(cfg: AppConfig, state: RuntimeState) -> None:
    if not can_trigger(state, "mic_toggle", cfg.timing.combo_cooldown_seconds):
        return

    mark_triggered(state, "mic_toggle")
    muted = toggle_mic(cfg)
    logger.info("Mic off" if muted else "Mic on")
    notify(cfg, "Mic off" if muted else "Mic on")


def trigger_volume_up(cfg: AppConfig, state: RuntimeState) -> None:
    if not can_trigger(state, "volume_up", cfg.timing.volume_cooldown_seconds):
        return

    mark_triggered(state, "volume_up")
    logger.info("Volume up")
    volume_up(cfg)


def trigger_volume_down(cfg: AppConfig, state: RuntimeState) -> None:
    if not can_trigger(state, "volume_down", cfg.timing.volume_cooldown_seconds):
        return

    mark_triggered(state, "volume_down")
    logger.info("Volume down")
    volume_down(cfg)


def trigger_poweroff(cfg: AppConfig, state: RuntimeState) -> None:
    if not can_trigger(state, "poweroff", cfg.timing.poweroff_cooldown_seconds):
        return

    mark_triggered(state, "poweroff")
    notify(cfg, "Powering off", "NyxPlay")
    poweroff(cfg)


def handle_abs_event(cfg: AppConfig, state: RuntimeState, code: int, value: int) -> None:
    if code == cfg.bindings.power_mod_analog_1:
        update_analog_state(state, "pow1", value, cfg)
        return

    if code == cfg.bindings.power_mod_analog_2:
        update_analog_state(state, "pow2", value, cfg)
        return

    if code == cfg.bindings.dpad_vertical_axis:
        state.pressed["dpad_up"] = value == cfg.bindings.dpad_up_value
        state.pressed["dpad_down"] = value == cfg.bindings.dpad_down_value
        return


def handle_key_down(cfg: AppConfig, state: RuntimeState, code: int) -> None:
    if code == cfg.bindings.primary_mod_1:
        state.pressed["mod1"] = True
        return

    if code == cfg.bindings.primary_mod_2:
        state.pressed["mod2"] = True
        return

    if modifiers_active(state) and power_modifiers_active(state):
        return

    if not modifiers_active(state):
        return

    if code == cfg.bindings.action_gamescope_on:
        start_hold_action(state, "gamescope_on")
    elif code == cfg.bindings.action_gamescope_off:
        start_hold_action(state, "gamescope_off")
    elif code == cfg.bindings.action_audio_toggle:
        start_hold_action(state, "audio_toggle")
    elif code == cfg.bindings.action_mic_toggle:
        start_hold_action(state, "mic_toggle")


def handle_key_up(cfg: AppConfig, state: RuntimeState, code: int) -> None:
    if code == cfg.bindings.primary_mod_1:
        state.pressed["mod1"] = False
        state.poweroff_started_at = None

        stop_hold_action(state, "gamescope_on")
        stop_hold_action(state, "gamescope_off")
        stop_hold_action(state, "audio_toggle")
        stop_hold_action(state, "mic_toggle")
        return

    if code == cfg.bindings.primary_mod_2:
        state.pressed["mod2"] = False
        state.poweroff_started_at = None

        stop_hold_action(state, "gamescope_on")
        stop_hold_action(state, "gamescope_off")
        stop_hold_action(state, "audio_toggle")
        stop_hold_action(state, "mic_toggle")
        return

    if code == cfg.bindings.action_gamescope_on:
        stop_hold_action(state, "gamescope_on")
    elif code == cfg.bindings.action_gamescope_off:
        stop_hold_action(state, "gamescope_off")
    elif code == cfg.bindings.action_audio_toggle:
        stop_hold_action(state, "audio_toggle")
    elif code == cfg.bindings.action_mic_toggle:
        stop_hold_action(state, "mic_toggle")


def handle_key_event(
    cfg: AppConfig,
    state: RuntimeState,
    device: InputDevice,
    code: int,
    value: int,
) -> None:
    _ = device

    if value == 1:
        handle_key_down(cfg, state, code)
    elif value == 0:
        handle_key_up(cfg, state, code)


def tick(cfg: AppConfig, state: RuntimeState, device: InputDevice) -> None:
    combo_active = modifiers_active(state) and power_modifiers_active(state)

    if combo_active:
        if state.poweroff_started_at is None:
            state.poweroff_started_at = now()
        elif now() - state.poweroff_started_at >= cfg.timing.poweroff_hold_seconds:
            trigger_poweroff(cfg, state)
            state.poweroff_started_at = None
    else:
        state.poweroff_started_at = None

    if modifiers_active(state):
        maybe_fire_hold_action(
            cfg,
            state,
            "gamescope_on",
            cfg.timing.hold_action_seconds,
            lambda: trigger_gamescope_on(cfg, state, device),
        )
        maybe_fire_hold_action(
            cfg,
            state,
            "gamescope_off",
            cfg.timing.hold_action_seconds,
            lambda: trigger_gamescope_off(cfg, state, device),
        )
        maybe_fire_hold_action(
            cfg,
            state,
            "audio_toggle",
            cfg.timing.hold_action_seconds,
            lambda: trigger_audio_toggle(cfg, state),
        )
        maybe_fire_hold_action(
            cfg,
            state,
            "mic_toggle",
            cfg.timing.hold_action_seconds,
            lambda: trigger_mic_toggle(cfg, state),
        )

        if state.pressed["dpad_up"]:
            trigger_volume_up(cfg, state)
        elif state.pressed["dpad_down"]:
            trigger_volume_down(cfg, state)
