from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass

from evdev import ecodes

logger = logging.getLogger("nyxplay")


@dataclass(slots=True)
class LockPinConfig:
    qs_binary: str = "/usr/bin/qs"
    qs_config: str = "ii"
    ipc_target: str = "lockpin"
    debounce_seconds: float = 0.12
    lock_state_cache_seconds: float = 0.5


class LockPinController:
    def __init__(self, config: LockPinConfig | None = None) -> None:
        self.config = config or LockPinConfig()
        self._last_action_at: dict[str, float] = {}
        self._lock_state_cached: bool = False
        self._lock_state_checked_at: float = 0.0

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
            self.config.ipc_target,
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
            logger.exception("LOCKPIN IPC failed for action=%s", action)
            return None

    def _query_lock_state(self) -> bool:
        result = self._run_qs_ipc("isLocked")
        if result is None:
            return False

        stdout = (result.stdout or "").strip().lower()
        stderr = (result.stderr or "").strip()

        logger.debug(
            "LOCKPIN isLocked rc=%s stdout=%r stderr=%r",
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

    def _ipc_call(self, action: str) -> None:
        if not self.is_lock_active():
            logger.debug("LOCKPIN ignored action=%s because screen is not locked", action)
            return

        result = self._run_qs_ipc(action)
        if result is None:
            return

        logger.debug(
            "LOCKPIN IPC action=%s rc=%s stdout=%r stderr=%r",
            action,
            result.returncode,
            result.stdout,
            result.stderr,
        )

    def left(self) -> None:
        if self._debounced("left"):
            self._ipc_call("left")

    def right(self) -> None:
        if self._debounced("right"):
            self._ipc_call("right")

    def accept(self) -> None:
        if self._debounced("accept"):
            self._ipc_call("accept")

    def backspace(self) -> None:
        if self._debounced("backspace"):
            self._ipc_call("backspace")

    def submit(self) -> None:
        if self._debounced("submit"):
            self._ipc_call("submit")

    def handle_event(self, event_code: int, event_value: int) -> bool:
        # BTN_SOUTH = A
        if event_code == ecodes.BTN_SOUTH and event_value == 1:
            self.accept()
            return True

        # BTN_EAST = B
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

        return False
