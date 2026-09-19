"""SoulSync 服务端配置。

环境变量优先，默认值面向单机部署（本机 gateway :10450 或任意 OpenAI 兼容端点）。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _int_env(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


def _float_env(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except (TypeError, ValueError):
        return default


@dataclass
class Settings:
    # ---- LLM（OpenAI 兼容端点；本机 GLM-5.3-Flash gateway 或任意 vLLM）----
    llm_base_url: str = field(
        default_factory=lambda: os.environ.get("SOULSYNC_LLM_BASE_URL", "http://127.0.0.1:10450/v1"))
    llm_api_key: str = field(
        default_factory=lambda: os.environ.get("SOULSYNC_LLM_API_KEY", "EMPTY"))
    llm_model: str = field(
        default_factory=lambda: os.environ.get("SOULSYNC_LLM_MODEL", "glm-5.3-flash"))
    llm_temperature: float = field(
        default_factory=lambda: _float_env("SOULSYNC_LLM_TEMPERATURE", 0.8))
    llm_max_tokens: int = field(
        default_factory=lambda: _int_env("SOULSYNC_LLM_MAX_TOKENS", 1024))

    # ---- Embedding（记忆向量化；bge-m3 或任意 OpenAI 兼容 embedding）----
    embed_base_url: str = field(
        default_factory=lambda: os.environ.get("SOULSYNC_EMBED_BASE_URL", ""))
    embed_model: str = field(
        default_factory=lambda: os.environ.get("SOULSYNC_EMBED_MODEL", "bge-m3"))
    embed_dim: int = field(default_factory=lambda: _int_env("SOULSYNC_EMBED_DIM", 1024))
    # embedding 服务不可用时降级为哈希向量（测试/离线模式）
    embed_fallback_hash: bool = field(
        default_factory=lambda: os.environ.get("SOULSYNC_EMBED_FALLBACK", "1") == "1")

    # ---- 存储 ----
    data_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("SOULSYNC_DATA_DIR", "~/.soulsync")).expanduser())
    db_path: Path = field(default=None)  # 在 __post_init__ 拼接

    # ---- 记忆引擎参数（SURVEY.md 九节设计决策 1/2）----
    memory_importance_gate: float = field(
        default_factory=lambda: _float_env("SOULSYNC_MEM_IMPORTANCE_GATE", 0.45))
    memory_recency_half_life_hours: float = field(
        default_factory=lambda: _float_env("SOULSYNC_MEM_HALF_LIFE_H", 72.0))
    memory_recall_top_k: int = field(
        default_factory=lambda: _int_env("SOULSYNC_MEM_TOPK", 8))
    reflection_interval_minutes: int = field(
        default_factory=lambda: _int_env("SOULSYNC_REFLECT_INTERVAL_MIN", 240))
    reflection_min_events: int = field(
        default_factory=lambda: _int_env("SOULSYNC_REFLECT_MIN_EVENTS", 6))

    # ---- 感知阈值（SURVEY.md 三/四节）----
    face_sim_threshold: float = field(
        default_factory=lambda: _float_env("SOULSYNC_FACE_SIM", 0.35))
    voice_sim_threshold: float = field(
        default_factory=lambda: _float_env("SOULSYNC_VOICE_SIM", 0.70))
    identity_cooccurrence_needed: int = field(
        default_factory=lambda: _int_env("SOULSYNC_COOC_NEEDED", 3))

    # ---- 主动智能（SURVEY.md 六节：内心独白门控+信任反馈）----
    proactive_enabled: bool = field(
        default_factory=lambda: os.environ.get("SOULSYNC_PROACTIVE", "1") == "1")
    proactive_score_threshold: float = field(
        default_factory=lambda: _float_env("SOULSYNC_PROACTIVE_THRESHOLD", 0.62))
    proactive_min_gap_minutes: int = field(
        default_factory=lambda: _int_env("SOULSYNC_PROACTIVE_GAP_MIN", 120))
    proactive_daily_cap: int = field(
        default_factory=lambda: _int_env("SOULSYNC_PROACTIVE_DAILY_CAP", 6))
    # 信任反馈：连续 N 次负面回应则降频冷却
    proactive_negative_backoff: int = field(
        default_factory=lambda: _int_env("SOULSYNC_PROACTIVE_BACKOFF", 3))

    # ---- 多语言 ----
    languages: tuple = ("zh", "en", "ja", "ko", "fr", "de", "es", "yue")
    default_language: str = field(
        default_factory=lambda: os.environ.get("SOULSYNC_LANG", "zh"))

    # ---- 安全（SURVEY.md 设计决策 6：危机旁路）----
    crisis_keywords_zh: tuple = ("自杀", "自残", "不想活", "轻生", "伤害自己")
    crisis_keywords_en: tuple = ("suicide", "kill myself", "self-harm", "end my life")
    crisis_hotline_zh: str = "全国心理援助热线 12356"
    crisis_hotline_default: str = "988 (US) / findahelpline.com"

    server_host: str = field(
        default_factory=lambda: os.environ.get("SOULSYNC_HOST", "0.0.0.0"))
    server_port: int = field(
        default_factory=lambda: _int_env("SOULSYNC_PORT", 8800))

    def __post_init__(self):
        if self.db_path is None:
            self.db_path = self.data_dir / "soulsync.db"
        self.data_dir.mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
