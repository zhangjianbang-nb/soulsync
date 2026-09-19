"""声纹识别（M4）：ECAPA-TDNN 惰性加载 + VAD 预处理 + 注册/识别。

首选 SpeechBrain ECAPA-TDNN（192 维）；缺失依赖时 is_available()=False。
单测注入 mock 引擎（直接喂向量），不依赖模型文件。
"""
from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np

from soulsync.config import get_settings
from soulsync.memory.store import MemoryStore


@dataclass
class VoiceMatch:
    identity_id: str | None
    similarity: float
    is_new: bool


class VoiceEngine:
    def __init__(self, store: MemoryStore):
        self.store = store
        s = get_settings()
        self.sim_threshold = s.voice_sim_threshold
        self._model = None
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        try:
            import speechbrain  # noqa: F401
            import torch  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from speechbrain.inference import SpeakerRecognition
                    self._model = SpeakerRecognition.from_hparams(
                        source="speechbrain/spkrec-ecapa-voxceleb",
                        savedir="pretrained_models/spkrec-ecapa-voxceleb")
        return self._model

    def embed_audio(self, wav: np.ndarray, sample_rate: int = 16000) -> list[float]:
        """wav float32 单声道 → 192 维归一化声纹。"""
        import torch
        model = self._get_model()
        if sample_rate != 16000:
            import librosa
            wav = librosa.resample(wav, orig_sr=sample_rate, target_sr=16000)
        tensor = torch.tensor(wav, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            emb = model.encode_batch(tensor)
        vec = emb.squeeze().numpy()
        vec = vec / (np.linalg.norm(vec) + 1e-9)
        return vec.tolist()

    def register(self, user_id: str, wav: np.ndarray, sample_rate: int = 16000,
                 label: str | None = None) -> VoiceMatch:
        vec = self.embed_audio(wav, sample_rate)
        return self._upsert(user_id, label, vec)

    def identify(self, user_id: str, wav: np.ndarray, sample_rate: int = 16000) -> VoiceMatch:
        vec = self.embed_audio(wav, sample_rate)
        return self._match(user_id, vec, self.sim_threshold)

    # 与 FaceEngine 共用 identities 表（modality='voice'）

    def _match(self, user_id: str, vec: list[float], threshold: float) -> VoiceMatch:
        rows = self.store.conn.execute(
            "SELECT label, data FROM identities WHERE user_id=? AND modality='voice'",
            (user_id,)).fetchall()
        best_label, best_sim = None, -1.0
        for r in rows:
            stored = np.frombuffer(r["data"], dtype=np.float32)
            sim = float(np.dot(stored, np.asarray(vec, dtype=np.float32)))
            if sim > best_sim:
                best_label, best_sim = r["label"], sim
        if best_label is None or best_sim < threshold:
            return VoiceMatch(None, max(best_sim, 0.0), is_new=True)
        return VoiceMatch(best_label, best_sim, is_new=False)

    def _upsert(self, user_id: str, label: str | None, vec: list[float]) -> VoiceMatch:
        match = self._match(user_id, vec, threshold=0.85)  # 高阈值合并采样
        arr = np.asarray(vec, dtype=np.float32)
        if match.identity_id is not None:
            row = self.store.conn.execute(
                "SELECT data, samples FROM identities WHERE user_id=? AND modality='voice' AND label=?",
                (user_id, match.identity_id)).fetchone()
            stored = np.frombuffer(row["data"], dtype=np.float32)
            n = row["samples"]
            merged = (stored * n + arr) / (n + 1)
            merged = merged / (np.linalg.norm(merged) + 1e-9)
            self.store.conn.execute(
                "UPDATE identities SET data=?, samples=? WHERE user_id=? AND modality='voice' AND label=?",
                (merged.tobytes(), n + 1, user_id, match.identity_id))
            self.store.conn.commit()
            return VoiceMatch(match.identity_id, match.similarity, is_new=False)
        new_label = label or f"voice_{len(self._labels(user_id)) + 1}"
        self.store.conn.execute(
            "INSERT OR REPLACE INTO identities (user_id,modality,label,dim,data,samples,created_at)"
            " VALUES (?,?,?,?,?,?,strftime('%s','now'))",
            (user_id, "voice", new_label, len(vec), arr.tobytes(), 1))
        self.store.conn.commit()
        return VoiceMatch(new_label, 1.0, is_new=True)

    def _labels(self, user_id: str) -> list[str]:
        rows = self.store.conn.execute(
            "SELECT label FROM identities WHERE user_id=? AND modality='voice'",
            (user_id,)).fetchall()
        return [r["label"] for r in rows]
