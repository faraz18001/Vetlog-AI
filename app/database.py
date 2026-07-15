from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.event import api
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.sql.expression import false

from app.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 20,
    },
)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class RawMessage(Base):
    __tablename__ = "raw_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_name = Column(String, nullable=False)
    sender = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(String, nullable=False)
    captured_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Users(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True)
    display_name = Column(String, nullable=False)
    password = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ConversationLog(Base):
    __tablename__ = "conversation_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String(64), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    thread_name = Column(String, nullable=False)
    turn_number = Column(Integer, nullable=False)
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    tool_name = Column(String, nullable=True)
    tool_args = Column(Text, nullable=True)
    tool_output = Column(Text, nullable=True)
    report_path = Column(String(512), nullable=True)
    table_path = Column(String(512), nullable=True)
    tokens_used = Column(Integer, nullable=True)


class UserSetting(Base):
    __tablename__ = "user_settings"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_provider"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(32), nullable=False, default="ollama")
    model = Column(String(128), nullable=False, default="")
    api_key = Column(Text, nullable=False, default="")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
