"""人脸识别（M3）：InsightFace buffalo_l 惰性加载 + 注册/识别。

依赖 insightface + onnxruntime（extras: perception）。缺失时 is_available()=False，
API 层返回 503 引导安装；单测用注入的 mock 引擎。
"""
from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np

from soulsync.config import get_settings
from soulsync.memory.store import MemoryStore


@dataclass
class FaceMatch:
    identity_id: str | None   # None=陌生人（未注册）
    similarity: float
    is_new: bool


class FaceEngine:
    """检测+识别+512 维嵌入。线程安全（模型加载一次）。"""

    def __init__(self, store: MemoryStore):
        self.store = store
        s = get_settings()
        self.sim_threshold = s.face_sim_threshold
        self._app = None
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        try:
            import insightface  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_app(self):
        if self._app is None:
            with self._lock:
                if self._app is None:
                    from insightface.app import FaceAnalysis
                    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
                    app.prepare(ctx_id=0, det_size=(640, 640))
                    self._app = app
        return self._app

    def embed_image(self, image_bgr: np.ndarray) -> list[float] | None:
        """取图中最大人脸的 512 维归一化嵌入；无人脸返回 None。"""
        app = self._get_app()
        faces = app.get(image_bgr)
        if not faces:
            return None
        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        vec = face.normed_embedding.tolist()
        return vec

    # ---------- 注册与识别 ----------

    def register(self, user_id: str, image_bgr: np.ndarray, label: str | None = None) -> FaceMatch:
        """注册/更新人脸嵌入（多次采样取均值提升鲁棒性）。"""
        vec = self.embed_image(image_bgr)
        if vec is None:
            raise ValueError("no face detected in image")
        return self._upsert(user_id, "face", label, vec)

    def identify(self, user_id: str, image_bgr: np.ndarray) -> FaceMatch:
        vec = self.embed_image(image_bgr)
        if vec is None:
            raise ValueError("no face detected in image")
        return self._match(user_id, "face", vec, self.sim_threshold)

    def _match(self, user_id: str, modality: str, vec: list[float],
               threshold: float) -> FaceMatch:
        rows = self.store.conn.execute(
            "SELECT label, data FROM identities WHERE user_id=? AND modality=?",
            (user_id, modality)).fetchall()
        best_label, best_sim = None, -1.0
        for r in rows:
            stored = np.frombuffer(r["data"], dtype=np.float32)
            sim = float(np.dot(stored, np.asarray(vec, dtype=np.float32)))
            if sim > best_sim:
                best_label, best_sim = r["label"], sim
        if best_label is None or best_sim < threshold:
            return FaceMatch(None, max(best_sim, 0.0), is_new=True)
        return FaceMatch(best_label, best_sim, is_new=False)

    def _upsert(self, user_id: str, modality: str, label: str | None,
                vec: list[float]) -> FaceMatch:
        """已有相近嵌入则均值合并，否则新建身份。"""
        match = self._match(user_id, modality, vec, threshold=-1.0)  # 看最近邻
        arr = np.asarray(vec, dtype=np.float32)
        if match.identity_id is not None and match.similarity >= 0.5:
            row = self.store.conn.execute(
                "SELECT data, samples FROM identities WHERE user_id=? AND modality=? AND label=?",
                (user_id, modality, match.identity_id)).fetchone()
            stored = np.frombuffer(row["data"], dtype=np.float32)
            n = row["samples"]
            merged = (stored * n + arr) / (n + 1)
            merged = merged / (np.linalg.norm(merged) + 1e-9)
            self.store.conn.execute(
                "UPDATE identities SET data=?, samples=? WHERE user_id=? AND modality=? AND label=?",
                (merged.tobytes(), n + 1, user_id, modality, match.identity_id))
            self.store.conn.commit()
            return FaceMatch(match.identity_id, match.similarity, is_new=False)
        new_label = label or f"{modality}_{len(self._labels(user_id, modality)) + 1}"
        self.store.conn.execute(
            "INSERT OR REPLACE INTO identities (user_id,modality,label,dim,data,samples,created_at)"
            " VALUES (?,?,?,?,?,?,strftime('%s','now'))",
            (user_id, modality, new_label, len(vec), arr.tobytes(), 1))
        self.store.conn.commit()
        return FaceMatch(new_label, 1.0, is_new=True)

    def _labels(self, user_id: str, modality: str) -> list[str]:
        rows = self.store.conn.execute(
            "SELECT label FROM identities WHERE user_id=? AND modality=?",
            (user_id, modality)).fetchall()
        return [r["label"] for r in rows]
