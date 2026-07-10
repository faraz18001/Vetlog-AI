from datetime import datetime, timedelta

import httpx

PROVIDERS = {
    "ollama": {"id": "ollama", "name": "Ollama"},
    "openai": {"id": "openai", "name": "OpenAI"},
    "gemini": {"id": "gemini", "name": "Gemini"},
    "groq": {"id": "groq", "name": "Groq"},
    "mistral": {"id": "mistral", "name": "Mistral"},
    "cerebras": {"id": "cerebras", "name": "Cerebras"},
    "openrouter": {"id": "openrouter", "name": "OpenRouter"},
}

_cache = {}  # {provider: (timestamp, [models...])}
_OLLAMA_BASE_URL = None


def _get_ollama_base_url() -> str:
    global _OLLAMA_BASE_URL
    if _OLLAMA_BASE_URL is None:
        import os
        _OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
    return _OLLAMA_BASE_URL


def _is_cache_valid(provider: str) -> bool:
    entry = _cache.get(provider)
    if not entry:
        return False
    ts, _ = entry
    return datetime.now() - ts < timedelta(hours=1)


async def fetch_ollama_models(api_key: str = "") -> list[str]:
    base_url = _get_ollama_base_url()
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    resp = httpx.get(
        base_url.rstrip("/") + "/api/tags",
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    models = []
    for m in data.get("models", []):
        name = m.get("name") or m.get("model")
        if name:
            models.append(name)
    return sorted(models)


async def fetch_openai_models(api_key: str) -> list[str]:
    resp = httpx.get(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    models = []
    for m in data.get("data", []):
        mid = m.get("id")
        if mid:
            models.append(mid)
    return sorted(models)


async def fetch_gemini_models(api_key: str) -> list[str]:
    resp = httpx.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        params={"key": api_key},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    models = []
    for m in data.get("models", []):
        name = m.get("name", "")
        name = name.replace("models/", "")
        supported = m.get("supportedGenerationMethods", [])
        if "generateContent" in supported and name:
            models.append(name)
    return sorted(models)


async def fetch_openai_compatible_models(
    base_url: str, api_key: str
) -> list[str]:
    url = base_url.rstrip("/") + "/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = httpx.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    models = []
    for m in data.get("data", []):
        mid = m.get("id")
        if mid:
            models.append(mid)
    return sorted(models)


async def get_models_for_provider(provider_id: str, api_key: str = "") -> dict:
    cache_key = provider_id

    if _is_cache_valid(cache_key):
        _, cached_models = _cache[cache_key]
        return {"provider": provider_id, "models": cached_models, "from_cache": True}

    try:
        if provider_id == "ollama":
            models = await fetch_ollama_models(api_key)
        elif provider_id == "openai":
            models = await fetch_openai_models(api_key)
        elif provider_id == "gemini":
            models = await fetch_gemini_models(api_key)
        elif provider_id in ("groq", "mistral", "cerebras", "openrouter"):
            base_urls = {
                "groq": "https://api.groq.com/openai",
                "mistral": "https://api.mistral.ai",
                "cerebras": "https://api.cerebras.ai",
                "openrouter": "https://openrouter.ai/api",
            }
            base_url = base_urls.get(provider_id)
            models = await fetch_openai_compatible_models(base_url, api_key)
        else:
            models = []

        _cache[cache_key] = (datetime.now(), models)
        return {"provider": provider_id, "models": models, "from_cache": False}

    except Exception as e:
        return {
            "provider": provider_id,
            "models": [],
            "error": str(e),
            "from_cache": False,
        }
