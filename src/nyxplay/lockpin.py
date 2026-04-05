from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass

from evdev import UInput, ecodes

logger = logging.getLogger("nyxplay")


@dataclass(slots=True)
class LockPinConfig:
    qs_binary: str = "/usr/bin/qs"
    qs_config: str = "ii"
    lock_ipc_target: str = "lock"
    debounce_seconds: float = 0.12
    lock_state_cache_seconds: float = 0.5
    key_press_delay_seconds: float = 0.01
    virtual_keyboard_name: str = "nyxplay-lockpad"


class LockPinController:
    def __init__(self, config: LockPinConfig | None = None) -> None:
        self.config = config or LockPinConfig()
        self._last_action_at: dict[str, float] = {}
        self._lock_state_cached: bool = False
        self._lock_state_checked_at: float = 0.0

        self._uinput = UInput(
            {
                ecodes.EV_KEY: [
                    ecodes.KEY_LEFT,
                    ecodes.KEY_RIGHT,
                    ecodes.KEY_UP,
                    ecodes.KEY_DOWN,
                    ecodes.KEY_ENTER,
                    ecodes.KEY_BACKSPACE,
                ]
            },
            name=self.config.virtual_keyboard_name,
        )

    def close(self) -> None:
        try:
            self._uinput.close()
        except Exception:
            logger.exception("Failed to close virtual keyboard")

    def _debounced(self, action: str) -> bool:
        now = time.monotonic()
        last = self._last_action_at.get(action, 0.0)

        if now - last < self.config.debounce_seconds:
            return False

        self._last_action_at[action] = now
        return True

    def _run_qs_ipc(self, action: str) -> subprocess.CompletedProcess[str] | None:
        cmd = [
            self.config.qs_binary,
            "-c",
            self.config.qs_config,
            "ipc",
            "call",
            self.config.lock_ipc_target,
            action,
        ]

        try:
            return subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=0.35,
            )
        except Exception:
            logger.exception("Lock IPC failed for action=%s", action)
            return None

    def _query_lock_state(self) -> bool:
        result = self._run_qs_ipc("isLocked")
        if result is None:
            return False

        stdout = (result.stdout or "").strip().lower()
        stderr = (result.stderr or "").strip()

        logger.debug(
            "LOCK state rc=%s stdout=%r stderr=%r",
            result.returncode,
            stdout,
            stderr,
        )

        if result.returncode != 0:
            return False

        return stdout == "true"

    def is_lock_active(self) -> bool:
        now = time.monotonic()

        if now - self._lock_state_checked_at < self.config.lock_state_cache_seconds:
            return self._lock_state_cached

        self._lock_state_cached = self._query_lock_state()
        self._lock_state_checked_at = now
        return self._lock_state_cached

    def _tap_key(self, keycode: int) -> None:
        if not self.is_lock_active():
            logger.debug("Ignoring key tap %s because screen is not locked", keycode)
            return

        try:
            self._uinput.write(ecodes.EV_KEY, keycode, 1)
            self._uinput.syn()
            time.sleep(self.config.key_press_delay_seconds)
            self._uinput.write(ecodes.EV_KEY, keycode, 0)
            self._uinput.syn()
        except Exception:
            logger.exception("Failed to emit virtual key %s", keycode)

    def left(self) -> None:
        if self._debounced("left"):
            self._tap_key(ecodes.KEY_LEFT)

    def right(self) -> None:
        if self._debounced("right"):
            self._tap_key(ecodes.KEY_RIGHT)

    def up(self) -> None:
        if self._debounced("up"):
            self._tap_key(ecodes.KEY_UP)

    def down(self) -> None:
        if self._debounced("down"):
            self._tap_key(ecodes.KEY_DOWN)

    def accept(self) -> None:
        if self._debounced("accept"):
            self._tap_key(ecodes.KEY_ENTER)

    def backspace(self) -> None:
        if self._debounced("backspace"):
            self._tap_key(ecodes.KEY_BACKSPACE)

    def handle_event(self, event_code: int, event_value: int) -> bool:
        if not self.is_lock_active():
            return False

        # BTN_SOUTH = A -> Enter
        if event_code == ecodes.BTN_SOUTH and event_value == 1:
            self.accept()
            return True

        # BTN_EAST = B -> Backspace
        if event_code == ecodes.BTN_EAST and event_value == 1:
            self.backspace()
            return True

        # ABS_HAT0X = D-pad horizontal
        if event_code == ecodes.ABS_HAT0X:
            if event_value == -1:
                self.left()
                return True
            if event_value == 1:
                self.right()
                return True

        # ABS_HAT0Y = D-pad vertical
        if event_code == ecodes.ABS_HAT0Y:
            if event_value == -1:
                self.up()
                return True
            if event_value == 1:
                self.down()
                return True

        return False
