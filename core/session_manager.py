from __future__ import annotations

import signal
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from config import CONFIG


@dataclass(frozen=True)
class SessionSnapshot:
    started_at: datetime
    now: datetime
    elapsed_seconds: float
    remaining_seconds: float
    max_runtime_seconds: float
    stop_requested: bool
    stop_reason: Optional[str]


class SessionManager:
    """
    Controls one manually-started analyst session.

    Responsibilities:
    - Maximum session duration enforcement.
    - Graceful Ctrl+C / termination handling.
    - Shared stop state for all system components.
    - Session timing information for the terminal UI and reports.

    It does NOT schedule sessions automatically.
    """

    def __init__(self, max_hours: float = CONFIG.MAX_SESSION_HOURS) -> None:
        if max_hours <= 0:
            raise ValueError("max_hours must be greater than zero.")

        self._max_runtime_seconds = float(max_hours) * 3600.0
        self._started_monotonic: Optional[float] = None
        self._started_at: Optional[datetime] = None

        self._stop_event = threading.Event()
        self._stop_reason: Optional[str] = None
        self._lock = threading.RLock()

        self._signals_installed = False
        self._previous_sigint = None
        self._previous_sigterm = None

    @property
    def started(self) -> bool:
        return self._started_monotonic is not None

    @property
    def started_at(self) -> datetime:
        if self._started_at is None:
            raise RuntimeError("Session has not been started.")
        return self._started_at

    @property
    def max_runtime_seconds(self) -> float:
        return self._max_runtime_seconds

    @property
    def stop_reason(self) -> Optional[str]:
        with self._lock:
            return self._stop_reason

    def start(self) -> None:
        with self._lock:
            if self.started:
                return

            self._started_monotonic = time.monotonic()
            self._started_at = datetime.now(timezone.utc)
            self._stop_event.clear()
            self._stop_reason = None

        self._install_signal_handlers()

    def request_stop(self, reason: str = "manual_stop") -> None:
        reason = str(reason).strip() or "manual_stop"

        with self._lock:
            if self._stop_event.is_set():
                return
            self._stop_reason = reason
            self._stop_event.set()

    def should_stop(self) -> bool:
        if not self.started:
            return False

        if self._stop_event.is_set():
            return True

        if self.elapsed_seconds() >= self._max_runtime_seconds:
            self.request_stop("max_session_runtime_reached")
            return True

        return False

    def wait(self, timeout: float) -> bool:
        """
        Wait for up to `timeout` seconds.

        Returns True when a stop was requested, otherwise False.
        This is preferable to time.sleep() because shutdown remains responsive.
        """
        if timeout < 0:
            raise ValueError("timeout cannot be negative.")

        if self.should_stop():
            return True

        stopped = self._stop_event.wait(timeout)
        return stopped or self.should_stop()

    def elapsed_seconds(self) -> float:
        if self._started_monotonic is None:
            return 0.0

        return max(0.0, time.monotonic() - self._started_monotonic)

    def remaining_seconds(self) -> float:
        return max(0.0, self._max_runtime_seconds - self.elapsed_seconds())

    def elapsed(self) -> timedelta:
        return timedelta(seconds=self.elapsed_seconds())

    def remaining(self) -> timedelta:
        return timedelta(seconds=self.remaining_seconds())

    def snapshot(self) -> SessionSnapshot:
        if not self.started:
            raise RuntimeError("Session has not been started.")

        # Calling should_stop here also enforces the time limit.
        self.should_stop()

        now = datetime.now(timezone.utc)
        return SessionSnapshot(
            started_at=self.started_at,
            now=now,
            elapsed_seconds=self.elapsed_seconds(),
            remaining_seconds=self.remaining_seconds(),
            max_runtime_seconds=self._max_runtime_seconds,
            stop_requested=self._stop_event.is_set(),
            stop_reason=self.stop_reason,
        )

    def close(self) -> None:
        if self.started and not self._stop_event.is_set():
            self.request_stop("session_closed")

        self._restore_signal_handlers()

    def _install_signal_handlers(self) -> None:
        if self._signals_installed:
            return

        # Python only permits signal registration from the main thread.
        if threading.current_thread() is not threading.main_thread():
            return

        def _handler(signum, _frame) -> None:
            if signum == signal.SIGINT:
                self.request_stop("keyboard_interrupt")
            else:
                self.request_stop("termination_signal")

        try:
            self._previous_sigint = signal.getsignal(signal.SIGINT)
            signal.signal(signal.SIGINT, _handler)

            if hasattr(signal, "SIGTERM"):
                self._previous_sigterm = signal.getsignal(signal.SIGTERM)
                signal.signal(signal.SIGTERM, _handler)

            self._signals_installed = True
        except (ValueError, OSError):
            # Session timing still works even if the runtime disallows signals.
            self._signals_installed = False

    def _restore_signal_handlers(self) -> None:
        if not self._signals_installed:
            return

        if threading.current_thread() is not threading.main_thread():
            return

        try:
            if self._previous_sigint is not None:
                signal.signal(signal.SIGINT, self._previous_sigint)

            if hasattr(signal, "SIGTERM") and self._previous_sigterm is not None:
                signal.signal(signal.SIGTERM, self._previous_sigterm)
        finally:
            self._signals_installed = False

    def __enter__(self) -> "SessionManager":
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is KeyboardInterrupt:
            self.request_stop("keyboard_interrupt")
        self.close()
