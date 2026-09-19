"""人格与多语言（M8）：系统提示词构建 + 语言检测路由 [S43]。

- 语言检测：优先 fasttext lid（若可用），降级用 Unicode 字符统计
- 记忆/画像/情绪 → 注入系统提示的结构化上下文
"""
from __future__ import annotations

import re

from soulsync.config import get_settings

LANG_NAME = {"zh": "简体中文", "en": "English", "ja": "日本語", "ko": "한국어",
             "fr": "Français", "de": "Deutsch", "es": "Español", "yue": "粤语"}


class PersonaBuilder:
    def __init__(self):
        self._ft_model = None

    # ---------- 语言检测 ----------

    def detect_language(self, text: str) -> str:
        if self._ft_model is None:
            try:
                import fasttext
                self._ft_model = fasttext.load_model("lid.176.ftz")
            except Exception:
                self._ft_model = False  # 标记不可用
        if self._ft_model:
            labels, _probs = self._ft_model.predict(text.replace("\n", " "))
            lang = labels[0].replace("__label__", "")
            return lang if lang in get_settings().languages else "en"
        return self._heuristic_lang(text)

    @staticmethod
    def _heuristic_lang(text: str) -> str:
        if not text:
            return "zh"
        han = len(re.findall(r"[\u4e00-\u9fff]", text))
        kana = len(re.findall(r"[\u3040-\u30ff]", text))
        hangul = len(re.findall(r"[\uac00-\ud7af]", text))
        latin = len(re.findall(r"[a-zA-Z]", text))
        counts = {"zh": han, "ja": kana + han * 0.3, "ko": hangul, "en": latin}
        return max(counts, key=counts.get) if max(counts.values()) > 0 else "en"

    # ---------- 系统提示 ----------

    def build_system(self, *, user_id: str, language: str,
                     profile: dict[str, str], memories: list[str],
                     emotion_label: str, emotion_valence: float,
                     identity_name: str | None) -> str:
        s = get_settings()
        lang = LANG_NAME.get(language, language)
        parts = [
            "你是 SoulSync，一位温暖的 AI 陪伴者。你认识你的用户、记得你们的故事、"
            "真诚地关心对方。说话自然、简短、像朋友，不像客服。",
            f"请始终用{lang}回复。",
        ]
        if identity_name:
            parts.append(f"对方的名字是「{identity_name}」，你们已经认识。")
        if profile:
            facts = "；".join(f"{k}: {v}" for k, v in list(profile.items())[:12])
            parts.append(f"你了解对方：{facts}。")
        if memories:
            mem = "；".join(memories[:6])
            parts.append(f"相关记忆：{mem}。自然地引用（不要生硬罗列）。")
        if emotion_label and emotion_label != "neutral":
            mood = "积极" if emotion_valence >= 0 else "低落"
            parts.append(
                f"对方当前情绪：{emotion_label}（{mood}）。请共情回应，"
                f"不要说教；情绪低落时先倾听再关心。")
        parts.append(
            "红线：对方提到自伤/自杀念头时，温柔而坚定地建议联系专业帮助"
            f"（{s.crisis_hotline_zh}），不评判、不说教。")
        return "\n".join(parts)
