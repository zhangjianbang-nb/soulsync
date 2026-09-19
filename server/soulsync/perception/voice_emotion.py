"""语音情绪 SER（M5 语音路）：emotion2vec / wav2vec2 可选集成。

依赖（extras: speech-emo）不可用时返回 None，编排器走能量特征兜底。
统一输出 VoiceEmotion(label, valence, arousal)。
"""
from __future__ import annotations

import threading

import numpy as np

from soulsync.emotion.fusion import VoiceEmotion

# 4 类情绪 → valence 映射（emotion2vec 输出 more 粒度时聚合）
VALENCE_MAP = {
    "happy": 0.7, "excited": 0.7, "surprised": 0.2,
    "sad": -0.6, "depressed": -0.7, "bored": -0.3,
    "angry": -0.7, "annoyed": -0.6,
    "neutral": 0.0, "calm": 0.1,
}
AROUSAL_MAP = {
    "happy": 0.6, "excited": 0.9, "surprised": 0.8,
    "sad": 0.2, "depressed": 0.15, "bored": 0.15,
    "angry": 0.85, "annoyed": 0.6,
    "neutral": 0.3, "calm": 0.2,
}


class VoiceEmotionEngine:
    def __init__(self):
        self._pipeline = None
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        try:
            import funasr  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_pipeline(self):
        if self._pipeline is None:
            with self._lock:
                if self._pipeline is None:
                    from funasr import AutoModel
                    # emotion2vec+ 官方微调模型（中英）；首次运行自动下载
                    self._pipeline = AutoModel(
                        model="iic/emotion2vec_plus_base",
                        disable_update=True)
        return self._pipeline

    def infer(self, wav: np.ndarray, sample_rate: int = 16000) -> VoiceEmotion | None:
        """wav float32 mono → 情绪。失败/不可用返回 None。"""
        if not self.is_available():
            return None
        try:
            import librosa
            if sample_rate != 16000:
                wav = librosa.resample(wav, orig_sr=sample_rate, target_sr=16000)
            model = self._get_pipeline()
            res = model.generate(wav, granularity="utterance", extract_embedding=False)
            if not res:
                return None
            labels = res[0].get("labels") or []
            scores = res[0].get("scores") or []
            if not labels:
                return None
            # 取 top1 label；标签形如 "</s>/happy/1.0" 需清洗
            top = labels[0] if isinstance(labels[0], str) else str
            label = top.strip("</s>").strip("/").split("/")[-2 if "/" in top else 0]
            label = label.lower()
            valence = VALENCE_MAP.get(label, 0.0)
            arousal = AROUSAL_MAP.get(label, 0.3)
            # 有概率分布时加权 valence
            if scores:
                try:
                    valence = sum(VALENCE_MAP.get((l or "").strip("</s>").strip("/").split("/")[-1].lower(), 0.0) * float(s) for l, s in zip(labels, scores))
                except Exception:
                    pass
            return VoiceEmotion(label=label, valence=max(-1.0, min(1.0, valence)), arousal=arousal)
        except Exception:
            return None
