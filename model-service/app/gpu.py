"""One inference at a time per model, with a bounded wait (docs/hardening.md #3, #4)."""

import threading
import time
from contextlib import contextmanager

from app.errors import ApiError


class GpuSlot:
    """Lock around a model's GPU work.

    Waiting is capped: Spring gives up after a few seconds, so a request queued longer than that only
    delays the next visitor. Past `wait_s` the caller gets 503 MODEL_BUSY at once. `started_at` lets
    /health spot an inference that never returns (hung driver).
    """

    def __init__(self, name: str, wait_s: float):
        self.name = name
        self.wait_s = wait_s
        self._lock = threading.Lock()
        self.started_at: float | None = None

    @contextmanager
    def __call__(self):
        if not self._lock.acquire(timeout=self.wait_s):
            raise ApiError(503, "MODEL_BUSY", f"{self.name} 모델이 다른 요청을 처리 중입니다. 잠시 후 다시 시도해 주세요.")
        self.started_at = time.monotonic()
        try:
            yield
        finally:
            self.started_at = None
            self._lock.release()

    def running_for(self) -> float:
        started = self.started_at
        return 0.0 if started is None else time.monotonic() - started
