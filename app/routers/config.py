import os
from fastapi import APIRouter
from app.schemas import LLMConfigResponse, LLMConfigUpdate
from app.config_manager import update_env_file
from app.agent import reload_agent

router = APIRouter(prefix="/api/config/llm", tags=["config"])

@router.get("", response_model=LLMConfigResponse)
def get_llm_config():
    """Return the currently configured LLM provider and model (without the API key)."""
    provider = os.getenv("AGENT_PROVIDER", "ollama").lower()
    provider_upper = provider.upper()
    
    if provider_upper == "GEMINI":
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    elif provider_upper == "OPENAI":
        model = os.getenv("DEFAULT_MODEL", "gpt-4o")
    else:
        model = os.getenv(f"{provider_upper}_MODEL", "")
        
    return LLMConfigResponse(provider=provider, model=model)

@router.post("")
def set_llm_config(payload: LLMConfigUpdate):
    """
    Update the active LLM provider, save to .env, and hot-reload the agent.
    WARNING: Hot-reloading wipes the short-term conversation memory of the current session.
    """
    update_env_file(payload.provider, payload.model, payload.api_key)
    
    # Hot reload the global agent so it picks up the new environment variables
    reload_agent()
    print(f"[Vetlog] Agent re-initialized with provider: {payload.provider}")
    
    return {"status": "success"}
