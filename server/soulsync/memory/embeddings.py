"""Embedding 客户端：OpenAI 兼容 /v1/embeddings；不可用时降级为确定性哈希向量。

哈希向量（feature hashing）保证无 embedding 服务时记忆系统仍可端到端测试，
但语义检索质量下降——生产部署应配置 bge-m3 等。
"""
from __future__ import annotations

import hashlib
import math

import httpx

from soulsync.config import get_settings


class EmbeddingClient:
    def __init__(self):
        s = get_settings()
        self.base_url = s.embed_base_url.rstrip("/")
        self.model = s.embed_model
        self.dim = s.embed_dim
        self.fallback = s.embed_fallback_hash

    async def embed(self, text: str) -> list[float]:
        if self.base_url:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    r = await client.post(
                        f"{self.base_url}/embeddings",
                        json={"model": self.model, "input": text},
                        headers={"Authorization": f"Bearer {get_settings().llm_api_key}"})
                r.raise_for_status()
                vec = r.json()["data"][0]["embedding"]
                if len(vec) != self.dim:
                    vec = _resize(vec, self.dim)
                return vec
            except Exception:
                if not self.fallback:
                    raise
        return self.hash_embed(text)

    def hash_embed(self, text: str, dim: int | None = None) -> list[float]:
        """Feature hashing：token 哈希到固定维度，符号交替，L2 归一化。"""
        dim = dim or self.dim
        vec = [0.0] * dim
        for tok in text.lower().split():
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            sign = 1.0 if (h >> 64) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


def _resize(vec: list[float], dim: int) -> list[float]:
    if len(vec) > dim:
        return vec[:dim]
    return vec + [0.0] * (dim - len(vec))
