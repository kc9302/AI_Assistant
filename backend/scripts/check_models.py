from app.agent.llm import provider_health
from app.core.settings import settings

health = provider_health()
print(
    {
        "provider": settings.LLM_PROVIDER,
        "base_url": health.base_url,
        "ok": health.ok,
        "details": health.details,
    }
)
