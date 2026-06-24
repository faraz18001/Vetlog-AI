from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RawMessageIn(BaseModel):
    chat_name: str
    sender: str
    text: str
    timestamp: str


class RawMessageBatchIn(BaseModel):
    messages: list[RawMessageIn]


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "web-session-default"


class ChatResponse(BaseModel):
    response: str
    thread_id: str


class RawMessageOut(BaseModel):
    id: int
    chat_name: str
    sender: str
    text: str
    timestamp: str
    captured_at: datetime

    model_config = {"from_attributes": True}
