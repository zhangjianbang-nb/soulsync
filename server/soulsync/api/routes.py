"""REST API：对话 / 注册 / 主动消息 / 记忆管理 / 会话结束。"""
from __future__ import annotations

import base64

import numpy as np
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from soulsync.config import get_settings


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=4000)
    face_b64: str | None = None      # JPEG/PNG base64（可选）
    voice_wav_b64: str | None = None # 16k mono float32 PCM base64（可选）
    sample_rate: int = 16000


class ChatResponse(BaseModel):
    reply: str
    turn_id: str
    identity: dict
    emotion: dict
    memories_used: list[str]
    crisis: bool


class ProactiveRequest(BaseModel):
    user_id: str


class NameRequest(BaseModel):
    user_id: str
    identity_id: str
    name: str = Field(min_length=1, max_length=32)


class ReactionRequest(BaseModel):
    user_id: str
    reaction: str = Field(pattern="^(positive|neutral|negative)$")


class MemoryOut(BaseModel):
    id: str
    layer: str
    content: str
    importance: float
    emotion: str | None
    created_at: float


def make_router(agent) -> APIRouter:
    router = APIRouter()

    @router.post("/v1/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest):
        from soulsync.agent.core import TurnInput
        face_bgr = _decode_image(req.face_b64)
        voice = _decode_wav(req.voice_wav_b64)
        out = await agent.turn(TurnInput(
            user_id=req.user_id, text=req.text,
            face_bgr=face_bgr, voice_wav=voice, sample_rate=req.sample_rate))
        return ChatResponse(
            reply=out.reply, turn_id=out.turn_id,
            identity={"id": out.identity.identity_id, "name": out.identity.name,
                      "confirmed": out.identity.confirmed, "is_new": out.identity.is_new},
            emotion={"label": out.emotion.label, "valence": out.emotion.valence,
                     "arousal": out.emotion.arousal, "source": out.emotion.source},
            memories_used=out.memories_used, crisis=out.crisis)

    @router.post("/v1/session/end")
    async def session_end(req: ProactiveRequest):
        await agent.on_session_end(req.user_id)
        return {"ok": True}

    @router.post("/v1/proactive")
    async def proactive(req: ProactiveRequest):
        msg = await agent.proactive_message(req.user_id)
        return {"message": msg}  # null=本次不主动

    @router.post("/v1/proactive/reaction")
    async def proactive_reaction(req: ReactionRequest):
        agent._proactive_engine().log_reaction(req.user_id, req.reaction)
        return {"ok": True}

    @router.get("/v1/memories/{user_id}", response_model=list[MemoryOut])
    async def memories(user_id: str, layer: str | None = None, limit: int = 50):
        rows = agent.store.list_memories(user_id, layer=layer, limit=min(limit, 200))
        return [MemoryOut(id=m.id, layer=m.layer, content=m.content,
                          importance=m.importance, emotion=m.emotion,
                          created_at=m.created_at) for m in rows]

    @router.delete("/v1/memories/{user_id}/{memory_id}")
    async def delete_memory(user_id: str, memory_id: str):
        agent.store.delete_memory(memory_id)
        return {"ok": True}

    @router.get("/v1/profile/{user_id}")
    async def profile(user_id: str):
        return agent.store.get_profile(user_id, include_sensitive=True)

    @router.delete("/v1/profile/{user_id}/{key}")
    async def delete_profile_key(user_id: str, key: str):
        ok = agent.store.delete_profile_key(user_id, key)
        if not ok:
            raise HTTPException(404, "key not found")
        return {"ok": True}

    @router.delete("/v1/user/{user_id}")
    async def forget_user(user_id: str):
        """被遗忘权 [S49]：删除该用户全部数据。"""
        agent.store.forget_user(user_id)
        return {"ok": True}

    @router.post("/v1/identity/name")
    async def set_identity_name(req: NameRequest):
        agent.resolver.set_name(req.user_id, req.identity_id, req.name)
        agent.store.set_profile(req.user_id, "name", req.name)
        return {"ok": True}

    @router.post("/v1/register/face")
    async def register_face(user_id: str = Form(...), label: str | None = Form(None),
                            image: UploadFile = File(...)):
        if not agent.face.is_available():
            raise HTTPException(503, "insightface not installed (pip install soulsync-server[perception])")
        data = await image.read()
        img = _decode_image_bytes(data)
        try:
            match = agent.face.register(user_id, img, label)
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
        return {"identity_id": match.identity_id, "is_new": match.is_new,
                "similarity": match.similarity}

    @router.post("/v1/register/voice")
    async def register_voice(user_id: str = Form(...), label: str | None = Form(None),
                             audio: UploadFile = File(...)):
        if not agent.voice.is_available():
            raise HTTPException(503, "speechbrain not installed (pip install soulsync-server[perception])")
        data = await audio.read()
        wav, sr = _decode_audio_file(data)
        match = agent.voice.register(user_id, wav, sr, label)
        return {"identity_id": match.identity_id, "is_new": match.is_new,
                "similarity": match.similarity}

    @router.get("/v1/health")
    async def health():
        s = get_settings()
        return {"status": "ok", "model": s.llm_model,
                "face": agent.face.is_available(), "voice": agent.voice.is_available()}

    return router


# ---------- 解码工具 ----------

def _decode_image(b64: str | None):
    if not b64:
        return None
    return _decode_image_bytes(base64.b64decode(b64))


def _decode_image_bytes(data: bytes):
    import cv2
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(422, "invalid image")
    return img


def _decode_wav(b64: str | None):
    if not b64:
        return None
    raw = base64.b64decode(b64)
    return np.frombuffer(raw, dtype=np.float32)


def _decode_audio_file(data: bytes):
    import io
    import soundfile as sf
    wav, sr = sf.read(io.BytesIO(data), dtype="float32")
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    return wav, sr
