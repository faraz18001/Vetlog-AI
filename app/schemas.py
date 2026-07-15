from datetime import datetime

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
    user_id: int | None = None


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0  # 0.0 means pricing not configured


class AgentStep(BaseModel):
    label: str  # Short human-readable title shown in the step chain
    detail: str  # Extra info (e.g. the SQL query, or row count)


class ChatResponse(BaseModel):
    response: str
    thread_id: str
    usage: TokenUsage | None = None
    report_path: str | None = None  # e.g. 'reports/daily_summary_2025-06-25_title.md'
    table_path: str | None = None  # e.g. 'reports/query_2025-06-30_143022.md'
    steps: list[AgentStep] = []  # Intermediate agent steps for the frontend step chain


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


class LLMConfigUpdate(BaseModel):
    provider: str
    model: str
    api_key: str


class LLMConfigResponse(BaseModel):
    provider: str
    model: str


class UserRegisterRequest(BaseModel):
    username: str
    display_name: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: int
    username: str
    display_name: str


class ConversationThread(BaseModel):
    thread_id: str
    thread_name: str
    updated_at: datetime


class ConversationMessage(BaseModel):
    role: str
    content: str
    thread_name: str
    created_at: datetime
    report_path: str | None = None
    table_path: str | None = None


class UserSettingsUpdate(BaseModel):
    provider: str
    model: str
    api_key: str


class UserSettingsResponse(BaseModel):
    provider: str
    model: str
    api_key_masked: str
    configured_providers: list[str] = []


class ProviderModelInfo(BaseModel):
    id: str
    name: str
    models: list[str]
