"""In-process counters exported to the ops dashboard (REQ-OBS-402)."""
from collections import Counter
from threading import Lock

_counts = Counter()
_lock = Lock()


def inc(name: str, by: int = 1) -> None:
    with _lock:
        _counts[name] += by


def get(name: str) -> int:
    return _counts[name]


def reset() -> None:
    with _lock:
        _counts.clear()


def snapshot() -> dict:
    with _lock:
        return dict(_counts)
