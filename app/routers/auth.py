from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from jose import jwt as jose_jwt
from sqlalchemy.orm import Session

from app.config import JWT_ALGORITHM, JWT_SECRET_KEY
from app.database import Users, get_session
from app.schemas import AuthResponse, LoginRequest, UserRegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def create_jwt(user: Users) -> str:
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jose_jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_session)):
    user = db.query(Users).filter(Users.username == payload.username).first()
    if not user or not bcrypt.checkpw(
        payload.password.encode("utf-8"), user.password.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return AuthResponse(
        token=create_jwt(user),
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
    )


@router.post("/register")
def register(payload: UserRegisterRequest, db: Session = Depends(get_session)):
    user_exists = db.query(Users).filter(Users.username == payload.username).first()
    if user_exists:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt())
    new_user = Users(
        username=payload.username,
        display_name=payload.display_name,
        password=hashed_password.decode(),
    )
    db.add(new_user)
    db.commit()
    return AuthResponse(
        token=create_jwt(new_user),  # JWT comes next
        user_id=new_user.id,  # new_user is available after db.add + db.commit
        username=payload.username,
        display_name=payload.display_name,
    )
