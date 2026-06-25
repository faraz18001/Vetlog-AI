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


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0  # 0.0 means pricing not configured


class ChatResponse(BaseModel):
    response: str
    thread_id: str
    usage: TokenUsage | None = None
    report_path: str | None = None  # e.g. 'reports/daily_summary_2025-06-25_title.md'


class UsageStats(BaseModel):
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost_usd: float
    pricing_configured: bool


class RawMessageOut(BaseModel):
    id: int
    chat_name: str
    sender: str
    text: str
    timestamp: str
    captured_at: datetime

    model_config = {"from_attributes": True}
