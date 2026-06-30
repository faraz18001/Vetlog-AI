from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime, timezone
from app.config import DATABASE_URL


engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 20  # Tells SQLite to wait 20 seconds for the door to unlock
    }
);
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


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()
