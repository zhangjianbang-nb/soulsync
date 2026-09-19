"""LLM 客户端：OpenAI 兼容 /chat/completions（GLM-5.3-Flash gateway / vLLM / 云端均可）。"""
from __future__ import annotations

import httpx

from soulsync.config import get_settings


class LLMClient:
    def __init__(self):
        s = get_settings()
        self.base_url = s.llm_base_url.rstrip("/")
        self.api_key = s.llm_api_key
        self.model = s.llm_model

    async def complete(self, prompt: str, *, system: str | None = None,
                       temperature: float | None = None,
                       max_tokens: int | None = None) -> str:
        s = get_settings()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else s.llm_temperature,
            "max_tokens": max_tokens or s.llm_max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{self.base_url}/chat/completions",
                                  json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
