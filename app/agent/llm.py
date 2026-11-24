"""Thin LLM interface so the model/provider can be swapped in one place."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app import config


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw_content: list[dict[str, Any]] = field(default_factory=list)  # assistant content blocks to replay


class LLM(Protocol):
    async def complete(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse: ...


class AnthropicLLM:
    def __init__(self, model: str | None = None):
        import anthropic

        self.client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        self.model = model or config.LLM_MODEL

    async def complete(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        resp = await self.client.messages.create(model=self.model, max_tokens=1500, system=system,
                                                 messages=messages, tools=tools)
        text_parts, calls, raw = [], [], []
        for b in resp.content:
            if b.type == "text":
                text_parts.append(b.text)
                raw.append({"type": "text", "text": b.text})
            elif b.type == "tool_use":
                calls.append(ToolCall(id=b.id, name=b.name, input=dict(b.input or {})))
                raw.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
        return LLMResponse(text="\n".join(text_parts).strip(), tool_calls=calls, raw_content=raw)


def get_llm() -> LLM | None:
    if not config.ANTHROPIC_API_KEY:
        return None
    return AnthropicLLM()
