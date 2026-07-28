from typing import List, Literal
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequestBody(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list

class LangGraphAgentResponse(BaseModel):
    """
    This model represents what the LangGraph Agent returns
    """
    messages: list