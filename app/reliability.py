import asyncio
import random
import time
import httpx
from app.providers.base import ChatResult, Provider



class CircuitBreaker:
    """Opens after N consecutive failures, then allows a retry after a cooldown."""

    def __init__(self, failure_threshold: int = 5, cooldown: float = 30.0):
        self.failure_threshold = failure_threshold
        self.cooldown = cooldown
        self.failures = 0
        self.opened_at: float | None = None

    def allow(self) -> bool:
        if self.opened_at is None:
            return True
        # after the cooldown, let a request through (half-open)
        return time.monotonic() - self.opened_at >= self.cooldown

    def record_success(self):
        self.failures = 0
        self.opened_at = None


    def record_failure(self):
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = time.monotonic()


def is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    return False


class AllProvidersFailed(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))




class Router:

    def __init__(self, providers: list[Provider], max_retries: int = 2, base_delay: float = 0.2):
        self.providers   = providers
        self.max_retries = max_retries
        self.base_delay  = base_delay
        self.breakers    = {p.name: CircuitBreaker() for p in providers}


    async def chat(self, model: str, messages: list[dict]) -> tuple[str, ChatResult]:
        errors: list[str] = []
        for provider in self.providers:
            breaker = self.breakers[provider.name]
            if not breaker.allow():
                errors.append(f"{provider.name}: circuit open")
                continue

            for attempt in range(self.max_retries + 1):
                try:
                    result = await provider.chat(model, messages)
                    breaker.record_success()
                    return provider.name, result
                except Exception as e:
                    if not is_retryable(e):
                        raise  # e.g. a 400 is our bug, retrying won't help
                    breaker.record_failure()
                    errors.append(f"{provider.name} attempt {attempt + 1}: {type(e).__name__}")
                    if attempt < self.max_retries and breaker.allow():
                        delay = self.base_delay * (2 ** attempt)
                        await asyncio.sleep(delay + random.uniform(0, delay / 2))  # jitter
                    else:
                        break
        raise AllProvidersFailed(errors)




