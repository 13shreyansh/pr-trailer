"""Login throttling (REQ-SEC-302): 5 failures lock the account for 15 minutes."""
import time

MAX_FAILURES = 5
LOCK_SECONDS = 15 * 60


class LoginLimiter:
    def __init__(self):
        self._failures = {}
        self._locked_until = {}

    def failed(self, user_id: str, now: float | None = None) -> None:
        now = time.time() if now is None else now
        count = self._failures.get(user_id, 0) + 1
        self._failures[user_id] = count
        if count >= MAX_FAILURES:
            self._locked_until[user_id] = now + LOCK_SECONDS
            self._failures[user_id] = 0

    def succeeded(self, user_id: str) -> None:
        self._failures.pop(user_id, None)

    def locked(self, user_id: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return now < self._locked_until.get(user_id, 0)
