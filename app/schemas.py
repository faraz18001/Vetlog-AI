from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RawMessageIn(BaseModel):
    chat_name: str
    sender: str
    text: str
    timestamp: str


class RawMessageBatchIn(BaseModel):
    messages: list[RawMessageIn]


class RawMessageOut(BaseModel):
    id: int
    chat_name: str
    sender: str
    text: str
    timestamp: str
    captured_at: datetime

    model_config = {"from_attributes": True}
