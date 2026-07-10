from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crypto import decrypt_api_key, encrypt_api_key
from app.database import UserSetting, get_session
from app.routers.auth import get_current_user
from app.schemas import ProviderModelInfo, UserSettingsResponse, UserSettingsUpdate

router = APIRouter(prefix="/api/user", tags=["settings"])

PROVIDER_MODELS = {
    "ollama": ProviderModelInfo(
        id="ollama",
        name="Ollama",
        models=[
            "gpt-oss:20b-cloud",
            "llama3",
            "llama3.1",
            "mistral",
            "qwen2.5",
            "deepseek-r1",
            "deepseek-v3",
            "phi4",
            "codellama",
        ],
    ),
    "openai": ProviderModelInfo(
        id="openai",
        name="OpenAI",
        models=[
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "o3-mini",
            "o1",
            "gpt-3.5-turbo",
        ],
    ),
    "gemini": ProviderModelInfo(
        id="gemini",
        name="Gemini",
        models=[
            "gemini-2.5-flash-lite",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ],
    ),
    "groq": ProviderModelInfo(
        id="groq",
        name="Groq",
        models=[
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
            "deepseek-r1-distill-llama-70b",
        ],
    ),
    "mistral": ProviderModelInfo(
        id="mistral",
        name="Mistral",
        models=[
            "mistral-small-latest",
            "mistral-medium-latest",
            "mistral-large-latest",
            "codestral-latest",
            "open-mistral-nemo",
        ],
    ),
    "cerebras": ProviderModelInfo(
        id="cerebras",
        name="Cerebras",
        models=[
            "llama-3.3-70b",
            "llama-3.1-8b",
            "llama-3.1-70b",
        ],
    ),
    "openrouter": ProviderModelInfo(
        id="openrouter",
        name="OpenRouter",
        models=[
            "auto:free",
            "openai/gpt-4o",
            "anthropic/claude-sonnet",
            "google/gemini-2.0-flash",
            "meta-llama/llama-3.3-70b",
        ],
    ),
}


def _mask_api_key(key: str) -> str:
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


@router.get("/settings", response_model=UserSettingsResponse)
def get_settings(
    user=Depends(get_current_user),
    db: Session = Depends(get_session),
):
    settings = (
        db.query(UserSetting)
        .filter(UserSetting.user_id == user.id)
        .first()
    )

    if not settings:
        return UserSettingsResponse(
            provider="ollama",
            model="",
            api_key_masked="",
        )

    plain_key = decrypt_api_key(settings.api_key)
    return UserSettingsResponse(
        provider=settings.provider,
        model=settings.model,
        api_key_masked=_mask_api_key(plain_key),
    )


@router.put("/settings")
def update_settings(
    payload: UserSettingsUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_session),
):
    settings = (
        db.query(UserSetting)
        .filter(UserSetting.user_id == user.id)
        .first()
    )

    if not settings:
        new_settings = UserSetting(
            user_id=user.id,
            provider=payload.provider,
            model=payload.model,
            api_key=encrypt_api_key(payload.api_key),
        )
        db.add(new_settings)
        db.commit()
        db.refresh(new_settings)
        return UserSettingsResponse(
            provider=new_settings.provider,
            model=new_settings.model,
            api_key_masked=_mask_api_key(payload.api_key),
        )

    settings.provider = payload.provider
    settings.model = payload.model
    settings.api_key = encrypt_api_key(payload.api_key)
    db.commit()
    db.refresh(settings)
    return UserSettingsResponse(
        provider=settings.provider,
        model=settings.model,
        api_key_masked=_mask_api_key(payload.api_key),
    )


@router.get("/config/providers")
def list_providers():
    return {"providers": list(PROVIDER_MODELS.values())}
