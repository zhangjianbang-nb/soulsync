"""LLM 客户端：OpenAI 兼容 /chat/completions（流式 + 非流式）。"""
from __future__ import annotations

from typing import AsyncIterator

import httpx

from soulsync.config import get_settings


class LLMClient:
    def __init__(self):
        s = get_settings()
        self.base_url = s.llm_base_url.rstrip("/")
        self.api_key = s.llm_api_key
        self.model = s.llm_model

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _payload(self, messages: list[dict], *, temperature: float | None,
                 max_tokens: int | None, stream: bool) -> dict:
        s = get_settings()
        return {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else s.llm_temperature,
            "max_tokens": max_tokens or s.llm_max_tokens,
            "stream": stream,
        }

    async def complete(self, prompt: str, *, system: str | None = None,
                       history: list[dict] | None = None,
                       temperature: float | None = None,
                       max_tokens: int | None = None) -> str:
        """非流式补全。history 为 [{"role","content"}] 多轮上下文。"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{self.base_url}/chat/completions",
                                  json=self._payload(messages, temperature=temperature,
                                                     max_tokens=max_tokens, stream=False),
                                  headers=self._headers())
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]

    async def stream(self, prompt: str, *, system: str | None = None,
                     history: list[dict] | None = None,
                     temperature: float | None = None,
                     max_tokens: int | None = None) -> AsyncIterator[str]:
        """SSE 流式补全：逐 token 产出文本增量。"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        async with httpx.AsyncClient(timeout=180) as client:
            async with client.stream(
                    "POST", f"{self.base_url}/chat/completions",
                    json=self._payload(messages, temperature=temperature,
                                       max_tokens=max_tokens, stream=True),
                    headers=self._headers()) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = _loads(data)
                    except Exception:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = (choices[0].get("delta") or {}).get("content")
                    if delta:
                        yield delta


def _loads(s: str) -> dict:
    import json
    return json.loads(s)
