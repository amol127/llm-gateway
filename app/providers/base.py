from abc import ABC, abstractmethod
from pydantic import BaseModel

class ChatResult(BaseModel):
    text: str
    model: str
    input_tokens: int
    output_tokens: int

class Provider(ABC):
    name: str

    @abstractmethod
    async def chat(self, model: str, messages: list[dict]) -> ChatResult:
        pass