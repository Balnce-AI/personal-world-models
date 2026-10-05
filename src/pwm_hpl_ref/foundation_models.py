from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, Sequence

from .canonical import canonical_json


SYSTEM_PROMPT_TEMPLATE = (
    "Use only the supplied personal-world projection. State uncertainty, do not infer withheld data, "
    "and return a JSON object with exactly the requested keys. Context: {context}"
)


@dataclass(frozen=True)
class Task:
    task_id: str
    instruction: str
    expected_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModelProjection:
    condition: str
    content: dict[str, Any]
    projection_id: str | None = None
    padding: str = ""
    information_ledger: tuple[dict[str, Any], ...] = ()
    control_applicable: bool | None = None


class TokenizerAdapter(Protocol):
    """Inspectable token counting contract used by matched experiments."""

    tokenizer_id: str
    revision: str
    chat_template_hash: str
    exact: bool
    verified: bool
    padding_token: str | None

    def encode(self, text: str) -> Sequence[int | str]: ...

    def count(self, text: str) -> int: ...


class DeterministicByteTokenizer:
    """Dependency-free byte tokenizer with a provably one-byte padding token."""

    tokenizer_id = "deterministic-byte-v1"
    revision = "1.0.0"
    chat_template_hash = "urn:pwm:prompt-template:deterministic-byte-v1"
    exact = True
    verified = True
    padding_token = "x"

    def encode(self, text: str) -> tuple[int, ...]:
        return tuple(text.encode("utf-8"))

    def count(self, text: str) -> int:
        return len(text.encode("utf-8"))


class DeterministicWhitespaceTokenizer:
    """Dependency-free lexical tokenizer for readable, deterministic diagnostics."""

    tokenizer_id = "deterministic-whitespace-v1"
    revision = "1.0.0"
    chat_template_hash = "urn:pwm:prompt-template:deterministic-whitespace-v1"
    exact = False
    verified = False
    padding_token = None

    def encode(self, text: str) -> tuple[str, ...]:
        return tuple(re.findall(r"\S+", text))

    def count(self, text: str) -> int:
        return len(self.encode(text))


def render_prompt(
    task: Task,
    context: ModelProjection,
    model_id: str,
    tools: list[ToolSpec] | None = None,
) -> str:
    """Render the complete provider request before any token accounting."""
    body: dict[str, Any] = {
        "model": model_id,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT_TEMPLATE.format(context=canonical_json(context.content).decode("utf-8")),
            },
            {"role": "user", "content": task.instruction + f" Required keys: {list(task.expected_keys)}"},
            {"role": "user", "content": context.padding},
        ],
    }
    if tools:
        body["tools"] = [
            {"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.input_schema}}
            for tool in tools
        ]
    return canonical_json(body).decode("utf-8")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class InferenceResult:
    output: Any
    model_id: str
    candidates: tuple[dict[str, Any], ...] = ()
    usage: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] | None = None
    confidence_ppm: int | None = None


class ReasoningModel(Protocol):
    model_id: str
    tokenizer: TokenizerAdapter | None

    def infer(
        self,
        task: Task,
        context: ModelProjection,
        tools: list[ToolSpec] | None = None,
    ) -> InferenceResult: ...


class LocalCallableModel:
    def __init__(self, model_id: str, infer_fn: Callable[[Task, ModelProjection], Any], tokenizer: TokenizerAdapter | None = None):
        self.model_id = model_id
        self._infer_fn = infer_fn
        self.tokenizer = tokenizer

    def infer(self, task: Task, context: ModelProjection, tools: list[ToolSpec] | None = None) -> InferenceResult:
        return InferenceResult(self._infer_fn(task, context), self.model_id)


class OpenAICompatibleModel:
    """Minimal provider-neutral HTTP adapter; credentials stay in the caller environment."""

    tokenizer = None

    def __init__(self, model_id: str, base_url: str, api_key: str | None = None, timeout_seconds: int = 120):
        self.model_id = model_id
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @property
    def experiment_parameters(self) -> dict[str, Any]:
        return {"adapter": "openai-compatible", "baseUrl": self.base_url, "temperature": 0, "timeoutSeconds": self.timeout_seconds}

    def infer(self, task: Task, context: ModelProjection, tools: list[ToolSpec] | None = None) -> InferenceResult:
        body = json.loads(render_prompt(task, context, self.model_id, tools))
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=canonical_json(body),
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            raw = json.loads(response.read())
        message = raw["choices"][0]["message"]
        candidates = tuple(message.get("model_candidates", ()))
        content = message.get("content", "")
        try:
            output = json.loads(content)
        except (TypeError, json.JSONDecodeError):
            output = content
        return InferenceResult(output, self.model_id, candidates, raw.get("usage", {}), raw)


class OllamaModel(OpenAICompatibleModel):
    def __init__(self, model_id: str, base_url: str = "http://localhost:11434/v1", timeout_seconds: int = 120):
        super().__init__(model_id, base_url, api_key=None, timeout_seconds=timeout_seconds)
