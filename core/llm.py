"""Language model access with an automatic provider fallback.

Groq serves Llama 3.3 at roughly 0.4s for a short reply, which is what makes a
conversational turn feel responsive. Gemini's free tier is the fallback for when
Groq rate-limits, which a free tier eventually will.

There is deliberately no tool-calling loop. The voice agent retrieves first and
then generates once, rather than letting the model decide to call a search tool
and waiting for a second round trip. One call per turn halves the latency a
caller hears, and the retrieval decision is cheap enough to make with a rule. The
trade-off is that the model cannot choose to search again after seeing poor
results; the abstention threshold covers that case by refusing instead.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from core.telemetry import Trace


@dataclass
class Reply:
    text: str
    provider: str = ""
    model: str = ""
    fell_back: bool = False
    error: str | None = None
    usage: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return bool(self.text.strip()) and self.error is None

    def as_json(self) -> dict | None:
        """Parse a JSON reply, tolerating a model that wraps it in a code fence."""
        raw = self.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1] if "```" in raw[3:] else raw.strip("`")
            raw = raw.removeprefix("json").strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start, end = raw.find("{"), raw.rfind("}")
            if 0 <= start < end:
                try:
                    return json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    return None
            return None


def _groq_model() -> str:
    return os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")


def _gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _call_groq(
    messages: list[dict], temperature: float, max_tokens: int, json_mode: bool
) -> Reply:
    from groq import Groq

    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set")

    client = Groq(api_key=key)
    kwargs: dict = {
        "model": _groq_model(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    usage = {}
    if getattr(response, "usage", None):
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
        }
    return Reply(
        text=(response.choices[0].message.content or "").strip(),
        provider="groq",
        model=_groq_model(),
        usage=usage,
    )


def _call_gemini(
    messages: list[dict], temperature: float, max_tokens: int, json_mode: bool
) -> Reply:
    from google import genai
    from google.genai import types

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    # Gemini takes the system instruction separately rather than as a message.
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    turns = [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part(text=m["content"])],
        )
        for m in messages
        if m["role"] != "system"
    ]

    config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        system_instruction=system or None,
        response_mime_type="application/json" if json_mode else None,
    )
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model=_gemini_model(), contents=turns, config=config
    )
    return Reply(
        text=(response.text or "").strip(),
        provider="gemini",
        model=_gemini_model(),
    )


def chat(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 400,
    json_mode: bool = False,
    trace: Trace | None = None,
) -> Reply:
    """Generate a reply, falling back to the secondary provider on failure.

    Temperature defaults low. The agent's job is to restate retrieved policy
    accurately, and creative variation in a stated waiting period is a defect.
    """
    order = [("groq", _call_groq), ("gemini", _call_gemini)]
    if os.getenv("LLM_PROVIDER", "groq").lower() == "gemini":
        order.reverse()

    failures: list[str] = []
    for index, (name, call) in enumerate(order):
        try:
            reply = call(messages, temperature, max_tokens, json_mode)
            reply.fell_back = index > 0
            if trace:
                trace.note(llm_provider=reply.provider, llm_model=reply.model)
                if reply.fell_back:
                    trace.note(llm_fallback_reason="; ".join(failures))
            return reply
        except Exception as exc:  # noqa: BLE001 - trying the next provider is the point
            failures.append(f"{name}: {type(exc).__name__}: {exc}")

    if trace:
        trace.note(llm_error="; ".join(failures))
    return Reply(text="", provider="none", error="; ".join(failures))
