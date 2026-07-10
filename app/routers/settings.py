from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.crypto import decrypt_api_key, encrypt_api_key
from app.database import UserSetting, get_session
from app.providers import PROVIDERS, get_models_for_provider
from app.routers.auth import get_current_user
from app.schemas import UserSettingsResponse, UserSettingsUpdate

router = APIRouter(prefix="/api/user", tags=["settings"])


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
    return {"providers": list(PROVIDERS.values())}


@router.get("/models")
async def list_models(
    provider: str = Query(..., description="Provider id (ollama, openai, gemini, ...)"),
    user=Depends(get_current_user),
    db: Session = Depends(get_session),
):
    settings = (
        db.query(UserSetting)
        .filter(UserSetting.user_id == user.id)
        .first()
    )

    api_key = ""
    if settings and settings.api_key:
        api_key = decrypt_api_key(settings.api_key)

    result = await get_models_for_provider(provider, api_key)
    return result
