import os
from pathlib import Path
from dotenv import set_key

# Assuming .env is at the root of the project
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

def update_env_file(provider: str, model: str, api_key: str):
    """
    Updates the .env file with the chosen LLM configuration.
    
    The mapping maps the generic 'api_key' and 'model' to the provider-specific
    environment variables that get_llm_model() expects.
    """
    if not ENV_PATH.exists():
        ENV_PATH.touch()

    # Always set the main provider
    set_key(str(ENV_PATH), "AGENT_PROVIDER", provider)
    
    # Set the provider-specific keys
    provider_upper = provider.upper()
    
    # We map 'gemini' to 'GOOGLE_API_KEY' and 'GEMINI_MODEL'
    if provider_upper == "GEMINI":
        set_key(str(ENV_PATH), "GOOGLE_API_KEY", api_key)
        set_key(str(ENV_PATH), "GEMINI_MODEL", model)
    elif provider_upper == "OPENAI":
        set_key(str(ENV_PATH), "OPENAI_API_KEY", api_key)
        set_key(str(ENV_PATH), "DEFAULT_MODEL", model)
    else:
        set_key(str(ENV_PATH), f"{provider_upper}_API_KEY", api_key)
        set_key(str(ENV_PATH), f"{provider_upper}_MODEL", model)
    
    # Update current os.environ so the change is immediate in the current process
    os.environ["AGENT_PROVIDER"] = provider
    if provider_upper == "GEMINI":
        os.environ["GOOGLE_API_KEY"] = api_key
        os.environ["GEMINI_MODEL"] = model
    elif provider_upper == "OPENAI":
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["DEFAULT_MODEL"] = model
    else:
        os.environ[f"{provider_upper}_API_KEY"] = api_key
        os.environ[f"{provider_upper}_MODEL"] = model
