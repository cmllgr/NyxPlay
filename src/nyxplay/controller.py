from __future__ import annotations

import logging
import os
import time

from evdev import InputDevice, ecodes

from .combos import RuntimeState, handle_abs_event, handle_key_event, tick
from .config import AppConfig
from .lockpin import LockPinController

logger = logging.getLogger("nyxplay")


def find_device_path(device_name: str, device_uniq: str | None = None) -> str | None:
    for entry in os.listdir("/dev/input"):
        if not entry.startswith("event"):
            continue

        path = f"/dev/input/{entry}"

        try:
            dev = InputDevice(path)
        except OSError:
            continue

        if dev.name != device_name:
            continue

        if device_uniq is not None and (dev.uniq or "").lower() != device_uniq.lower():
            continue

        return path

    return None


def wait_for_device(cfg: AppConfig) -> str:
    announced_missing = False

    while True:
        path = find_device_path(cfg.device.name, cfg.device.uniq)
        if path is not None:
            if announced_missing:
                logger.info("Controller detected")
            return path

        if not announced_missing:
            logger.warning("Controller not found, waiting...")
            announced_missing = True

        time.sleep(cfg.timing.device_poll_seconds)


def run_listener(cfg: AppConfig) -> None:
    state = RuntimeState()
    lockpin = LockPinController()

    try:
        while True:
            device_path = wait_for_device(cfg)

            try:
                device = InputDevice(device_path)
                device_grabbed = False

                logger.info("Connected to %s (%s)", device.path, device.name)
                state.reset()

                while True:
                    lock_active = lockpin.is_lock_active()

                    if lock_active and not device_grabbed:
                        try:
                            device.grab()
                            device_grabbed = True
                            state.reset()
                            logger.info("Controller grabbed for lock screen")
                        except OSError as exc:
                            logger.warning("Failed to grab controller: %s", exc)

                    elif not lock_active and device_grabbed:
                        try:
                            device.ungrab()
                            logger.info("Controller released after lock screen")
                        except OSError as exc:
                            logger.warning("Failed to ungrab controller: %s", exc)
                        finally:
                            device_grabbed = False
                            state.reset()

                    event = device.read_one()

                    while event is not None:
                        # While locked, swallow every controller event so nothing
                        # leaks to gamescope / Steam / the game in background.
                        if lock_active:
                            if event.type in (ecodes.EV_ABS, ecodes.EV_KEY):
                                lockpin.handle_event(event.code, event.value)

                            event = device.read_one()
                            continue

                        if event.type == ecodes.EV_ABS:
                            handle_abs_event(cfg, state, event.code, event.value)
                        elif event.type == ecodes.EV_KEY:
                            handle_key_event(cfg, state, device, event.code, event.value)

                        event = device.read_one()

                    if not lock_active:
                        tick(cfg, state, device)

                    time.sleep(cfg.timing.loop_sleep_seconds)

            except OSError as exc:
                logger.warning("Device error: %s. Waiting again...", exc)
                time.sleep(1.0)
            except Exception as exc:
                logger.exception("Unexpected error: %s", exc)
                time.sleep(2.0)
            finally:
                try:
                    device.ungrab()
                except Exception:
                    pass
    finally:
        lockpin.close()
