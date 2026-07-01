from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

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


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


"""1.We will later add a table for saving users setting we can't put the model selection and api key inside the
env
2.we might need to grab the provided models on that specific select api so that user can easily select its model.
3.we also need to add a database tables for keeping track of all the chat histrory on the sidebar"""
