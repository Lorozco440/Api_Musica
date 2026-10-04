from collections import deque
from threading import Lock
from time import monotonic
from fastapi import HTTPException, Request


class RateLimiter:
    """Bounded, per-process IP limit for the academic single-worker deployment."""
    def __init__(self, limit=10, window=60):
        self.limit, self.window = limit, window
        self.entries = {}
        self.lock = Lock()

    def check(self, request: Request):
        key = request.client.host if request.client else "unknown"
        now = monotonic()
        with self.lock:
            expired = [k for k, v in self.entries.items() if not v or v[-1] <= now - self.window]
            for k in expired:
                del self.entries[k]
            if key not in self.entries and len(self.entries) >= 10000:
                raise HTTPException(429, "Demasiadas solicitudes", headers={"Retry-After": str(self.window)})
            attempts = self.entries.setdefault(key, deque())
            while attempts and attempts[0] <= now - self.window:
                attempts.popleft()
            if len(attempts) >= self.limit:
                raise HTTPException(429, "Demasiados intentos; espere un minuto", headers={"Retry-After": str(self.window)})
            attempts.append(now)


limiter = RateLimiter()
