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


def is_quota_exhausted(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
        body = exc.response.text
        return "RESOURCE_EXHAUSTED" in body or "per day" in body
    return False

class AllProvidersFailed(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


class UnknownModel(Exception):
    pass

class Router:

    def __init__(self, providers: list[Provider], max_retries: int = 2,
                 base_delay: float = 0.2, routes: dict[str, list[tuple[str, str]]] | None = None):
        self.providers = providers
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.breakers = {p.name: CircuitBreaker() for p in providers}
        self.by_name = {p.name: p for p in providers}
        self.routes = routes  # alias -> [(provider_name, provider_model), ...] in fallback order

    def _candidates(self, model: str) -> list[tuple[Provider, str]]:
        if self.routes is None:  # old behaviour, keeps your existing tests working
            return [(p, model) for p in self.providers]
        if model not in self.routes:
            raise UnknownModel(model)
        return [(self.by_name[name], provider_model) for name, provider_model in self.routes[model]]


    async def chat(self, model: str, messages: list[dict]) -> tuple[str, ChatResult]:
        errors: list[str] = []
        # for provider in self.providers:
        for provider, provider_model in self._candidates(model):
            breaker = self.breakers[provider.name]
            if not breaker.allow():
                errors.append(f"{provider.name}: circuit open")
                continue

            for attempt in range(self.max_retries + 1):
                try:
                    # result = await provider.chat(model, messages)
                    result = await provider.chat(provider_model, messages)
                    breaker.record_success()
                    return provider.name, result
                except Exception as e:
                    if not is_retryable(e):
                        raise  # e.g. a 400 is our bug, retrying won't help

                    if is_quota_exhausted(e):
                        breaker.record_failure()
                        errors.append(f"{provider.name}: quota exhausted")
                        break  # don't retry, move to the next provider

                    breaker.record_failure()
                    errors.append(f"{provider.name} attempt {attempt + 1}: {type(e).__name__}")
                    if attempt < self.max_retries and breaker.allow():
                        delay = self.base_delay * (2 ** attempt)
                        await asyncio.sleep(delay + random.uniform(0, delay / 2))  # jitter
                    else:
                        break
        raise AllProvidersFailed(errors)




