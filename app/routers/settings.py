from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.crypto import decrypt_api_key, encrypt_api_key
from app.database import UserSetting, get_session
from app.providers import PROVIDERS, get_models_for_provider
from app.routers.auth import get_current_user
from app.schemas import UserSettingsResponse, UserSettingsUpdate

router = APIRouter(prefix="/user", tags=["settings"])


def _mask_api_key(key: str) -> str:
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


def _list_configured_providers(user_id: int, db: Session) -> list[str]:
    rows = (
        db.query(UserSetting.provider)
        .filter(UserSetting.user_id == user_id)
        .all()
    )
    return [r[0] for r in rows]


@router.get("/settings", response_model=UserSettingsResponse)
def get_settings(
    provider: str = Query("", description="Load settings for a specific provider. Empty = most recently active."),
    user=Depends(get_current_user),
    db: Session = Depends(get_session),
):
    query = db.query(UserSetting).filter(UserSetting.user_id == user.id)

    if provider:
        query = query.filter(UserSetting.provider == provider)
    else:
        query = query.order_by(desc(UserSetting.updated_at))

    settings = query.first()

    configured = _list_configured_providers(user.id, db)

    if not settings:
        return UserSettingsResponse(
            provider=provider if provider else "ollama",
            model="",
            api_key_masked="",
            configured_providers=configured,
        )

    plain_key = decrypt_api_key(settings.api_key)
    return UserSettingsResponse(
        provider=settings.provider,
        model=settings.model,
        api_key_masked=_mask_api_key(plain_key),
        configured_providers=configured,
    )


@router.put("/settings")
def update_settings(
    payload: UserSettingsUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_session),
):
    settings = (
        db.query(UserSetting)
        .filter(
            UserSetting.user_id == user.id,
            UserSetting.provider == payload.provider,
        )
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
            configured_providers=_list_configured_providers(user.id, db),
        )

    if payload.model:
        settings.model = payload.model
    if payload.api_key:
        settings.api_key = encrypt_api_key(payload.api_key)
    db.commit()
    db.refresh(settings)
    return UserSettingsResponse(
        provider=settings.provider,
        model=settings.model,
        api_key_masked=_mask_api_key(payload.api_key) if payload.api_key else _mask_api_key(decrypt_api_key(settings.api_key)),
        configured_providers=_list_configured_providers(user.id, db),
    )


@router.get("/config/providers")
def list_providers():
    return {"providers": list(PROVIDERS.values())}


@router.get("/models")
async def list_models(
    provider: str = Query(..., description="Provider id (ollama, openai, gemini, ...)"),
    api_key: str = Query("", description="Optional API key override (uses saved key if empty)"),
    user=Depends(get_current_user),
    db: Session = Depends(get_session),
):
    if not api_key:
        settings = (
            db.query(UserSetting)
            .filter(
                UserSetting.user_id == user.id,
                UserSetting.provider == provider,
            )
            .first()
        )
        if settings and settings.api_key:
            api_key = decrypt_api_key(settings.api_key)

    if not api_key and provider != "ollama":
        return {
            "provider": provider,
            "models": [],
            "error": "API key is required for " + provider + ". Enter it and press Enter.",
        }

    result = await get_models_for_provider(provider, api_key)
    return result
