"""情绪融合（M6）：文本情绪（LLM 结构化输出）+ 语音情绪（emotion2vec/SER）传感器融合 [S28][S31]。

规则加权：双路一致→取均值；冲突→语音权重更高（语气比措辞诚实）；
单路缺失→用另一路。输出统一 EmotionState。
"""
from __future__ import annotations

from dataclasses import dataclass, field

EMOTIONS = ("happy", "sad", "angry", "anxious", "neutral")


@dataclass
class EmotionState:
    label: str = "neutral"
    valence: float = 0.0        # -1 负 .. +1 正
    arousal: float = 0.0        # 0 平静 .. 1 激动
    source: str = "none"        # text | voice | fused | none
    crisis: bool = False        # 危机语境标记 [S49][S50]


@dataclass
class TextEmotion:
    label: str = "neutral"
    valence: float = 0.0
    crisis: bool = False


@dataclass
class VoiceEmotion:
    label: str = "neutral"
    valence: float = 0.0
    arousal: float = 0.5


VALENCE_TABLE = {
    "happy": 0.7, "sad": -0.6, "angry": -0.7, "anxious": -0.4, "neutral": 0.0,
}
AROUSAL_TABLE = {
    "happy": 0.6, "sad": 0.25, "angry": 0.85, "anxious": 0.7, "neutral": 0.3,
}


class EmotionFusion:
    def __init__(self, crisis_keywords: tuple[str, ...] = ()):
        self.crisis_keywords = crisis_keywords

    def fuse(self, text: TextEmotion | None, voice: VoiceEmotion | None) -> EmotionState:
        crisis = bool(text and text.crisis)
        if text and voice:
            if text.label == voice.label:
                return EmotionState(text.label, text.valence, voice.arousal, "fused", crisis)
            # 冲突：语音权重 0.6 > 文本 0.4 [S28]
            v = 0.4 * self._tv(text.label) + 0.6 * self._vv(voice)
            label = voice.label if abs(v - text.valence) > 0.2 else text.label
            return EmotionState(label, v, voice.arousal, "fused", crisis)
        if text:
            return EmotionState(text.label, text.valence, AROUSAL_TABLE[text.label], "text", crisis)
        if voice:
            return EmotionState(voice.label, voice.valence, voice.arousal, "voice", crisis)
        return EmotionState()

    def detect_crisis(self, text: str) -> bool:
        t = text.lower()
        return any(k in t for k in self.crisis_keywords)

    def _tv(self, label: str) -> float:
        return VALENCE_TABLE.get(label, 0.0)

    def _vv(self, v: VoiceEmotion) -> float:
        return v.valence if v.valence is not None else VALENCE_TABLE.get(v.label, 0.0)
