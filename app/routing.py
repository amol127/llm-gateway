from app.config import settings
from app.providers.gemini import GeminiProvider
from app.providers.mock import MockProvider
from app.reliability import Router


def build_router() -> Router:
    providers = [MockProvider(name="mock", latency=0.05)]
    routes = {"mock": [("mock", "mock-1")]}
    if settings.gemini_api_key.get_secret_value():
        providers.append(GeminiProvider())
        routes["fast"] = [("gemini", "gemini-2.5-flash")]
    return Router(providers, routes=routes)