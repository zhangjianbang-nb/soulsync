"""Agent 编排器：一轮对话的完整流水线。

输入（文本/可选人脸帧/可选语音）→ 感知识别 → 情绪融合 → 记忆检索 →
危机检查（旁路）[S49] → LLM 生成 → 记忆写入队列 → 会话末反思。

工作记忆 L1 = 每用户最近 N 轮的内存 buffer（不落库）。
"""
from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field

import numpy as np

from soulsync.agent.llm import LLMClient
from soulsync.agent.persona import PersonaBuilder
from soulsync.config import get_settings
from soulsync.emotion.fusion import EmotionFusion, EmotionState, TextEmotion, VoiceEmotion
from soulsync.memory.embeddings import EmbeddingClient
from soulsync.memory.reflector import Reflector, TurnRecord
from soulsync.memory.store import MemoryStore
from soulsync.perception.face import FaceEngine, FaceMatch
from soulsync.perception.fuse import IdentityResolver, ResolvedIdentity
from soulsync.perception.voice import VoiceEngine, VoiceMatch
from soulsync.perception.voice_emotion import VoiceEmotionEngine


@dataclass
class TurnInput:
    user_id: str
    text: str
    face_bgr: np.ndarray | None = None       # 可选：摄像头帧
    voice_wav: np.ndarray | None = None      # 可选：语音片段（16k mono f32）
    sample_rate: int = 16000


@dataclass
class TurnOutput:
    reply: str
    identity: ResolvedIdentity
    emotion: EmotionState
    memories_used: list[str] = field(default_factory=list)
    crisis: bool = False
    turn_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


class CompanionAgent:
    def __init__(self, store: MemoryStore):
        self.store = store
        s = get_settings()
        self.llm = LLMClient()
        self.embedder = EmbeddingClient()
        self.persona = PersonaBuilder()
        self.face = FaceEngine(store)
        self.voice = VoiceEngine(store)
        self.voice_emo = VoiceEmotionEngine()
        self.resolver = IdentityResolver(store)
        self.emotion_fusion = EmotionFusion(
            crisis_keywords=s.crisis_keywords_zh + s.crisis_keywords_en)
        self.reflector = Reflector(store, self.embedder, self.llm)
        self._working: dict[str, deque[TurnRecord]] = defaultdict(
            lambda: deque(maxlen=12))
        self._pending_reflect: dict[str, float] = defaultdict(float)

    # ---------- 单轮对话 ----------

    async def turn(self, inp: TurnInput) -> TurnOutput:
        s = get_settings()
        uid = inp.user_id

        # 1) 感知：人脸+声纹识别 → 身份融合
        face_match = self._try_face(uid, inp)
        voice_match = self._try_voice(uid, inp)
        identity = self.resolver.resolve(uid, face_match, voice_match)

        # 2) 情绪：文本(LLM 快判) + 语音(SER 可用则跑) → 融合
        text_emo = TextEmotion(crisis=self.emotion_fusion.detect_crisis(inp.text))
        voice_emo = self._try_voice_emotion(inp)
        emotion = self.emotion_fusion.fuse(text_emo, voice_emo)

        # 3) 危机旁路 [S49][S50]：不走个性化逻辑
        if emotion.crisis:
            reply = self._crisis_reply(inp.text)
            self._remember(uid, inp, reply, emotion)
            return TurnOutput(reply, identity, emotion, crisis=True)

        # 4) 记忆检索（三维打分）
        qvec = await self.embedder.embed(inp.text)
        hits = self.store.search(uid, qvec, top_k=s.memory_recall_top_k)
        memories_used = [h[0].content for h in hits]

        # 5) LLM 生成（多轮上下文进 messages）
        system = self.persona.build_system(
            user_id=uid, language=self.persona.detect_language(inp.text),
            profile=self.store.get_profile(uid), memories=memories_used,
            emotion_label=emotion.label, emotion_valence=emotion.valence,
            identity_name=identity.name)
        history = self._build_history(uid)

        reply = await self.llm.complete(inp.text, system=system, history=history)

        # 6) 写入工作记忆 + 待反思队列
        self._remember(uid, inp, reply, emotion)

        # 7) 周期性反思（会话末由 API 层触发 consolidate/reflect）
        return TurnOutput(reply, identity, emotion, memories_used)

    async def turn_stream(self, inp: TurnInput):
        """流式版 turn：先做感知/情绪/检索，再逐 token yield。

        产出: 先 dict（元信息：identity/emotion/memories/crisis），后 str 增量，
        结束时 dict（{"done": true, "turn_id", "reply"}）。
        """
        s = get_settings()
        uid = inp.user_id

        face_match = self._try_face(uid, inp)
        voice_match = self._try_voice(uid, inp)
        identity = self.resolver.resolve(uid, face_match, voice_match)

        text_emo = TextEmotion(crisis=self.emotion_fusion.detect_crisis(inp.text))
        voice_emo = self._try_voice_emotion(inp)
        emotion = self.emotion_fusion.fuse(text_emo, voice_emo)

        if emotion.crisis:
            reply = self._crisis_reply(inp.text)
            self._remember(uid, inp, reply, emotion)
            yield {"identity": identity.name, "emotion": emotion.label,
                   "memories": [], "crisis": True}
            yield reply
            yield {"done": True, "reply": reply}
            return

        qvec = await self.embedder.embed(inp.text)
        hits = self.store.search(uid, qvec, top_k=s.memory_recall_top_k)
        memories_used = [h[0].content for h in hits]

        system = self.persona.build_system(
            user_id=uid, language=self.persona.detect_language(inp.text),
            profile=self.store.get_profile(uid), memories=memories_used,
            emotion_label=emotion.label, emotion_valence=emotion.valence,
            identity_name=identity.name)
        history = self._build_history(uid)

        yield {"identity": identity.name, "emotion": emotion.label,
               "memories": memories_used, "crisis": False}

        parts: list[str] = []
        async for delta in self.llm.stream(inp.text, system=system, history=history):
            parts.append(delta)
            yield delta
        reply = "".join(parts)
        self._remember(uid, inp, reply, emotion)
        yield {"done": True, "reply": reply}

    def _build_history(self, uid: str) -> list[dict]:
        """工作记忆 → messages（成对 user/assistant，去掉最后半轮）。"""
        msgs: list[dict] = []
        for rec in list(self._working[uid])[:-1] if self._working[uid] else []:
            msgs.append({"role": "user", "content": rec.user_text})
            msgs.append({"role": "assistant", "content": rec.assistant_text})
        return msgs

    # ---------- 会话结束：反思 ----------

    async def on_session_end(self, user_id: str):
        turns = list(self._working[user_id])
        if turns:
            await self.reflector.extract_episodic(user_id, turns)
        await self.reflector.consolidate(user_id)
        await self.reflector.reflect(user_id)

    # ---------- 主动消息生成 ----------

    def _proactive_engine(self):
        from soulsync.agent.proactive import ProactiveEngine
        if not hasattr(self, "_proactive"):
            self._proactive = ProactiveEngine(self.store)
        return self._proactive

    async def proactive_message(self, user_id: str) -> str | None:
        self._proactive_engine()
        decision = self._proactive.evaluate(user_id)
        if not decision.should_speak or decision.candidate is None:
            return None
        cand = decision.candidate
        memories = [h[0].content for h in self.store.search(
            user_id, self.embedder.hash_embed("关心 问候 近况"), top_k=3)]
        prompt = (
            f"你是用户的 AI 陪伴者。请主动发一条简短（1-2 句）自然的问候/关心消息。\n"
            f"触发原因：{cand.reason}（{cand.trigger}）。\n"
            f"可参考的记忆：{'；'.join(memories) if memories else '无'}。\n"
            "要求：引用具体记忆（如适用）、不问的第二句话不要有、别像通知。直接输出消息内容。")
        msg = await self.llm.complete(prompt, temperature=0.9, max_tokens=120)
        self._proactive.log_proactive(user_id, cand, msg)
        return msg

    # ---------- 内部 ----------

    def _try_face(self, uid: str, inp: TurnInput) -> FaceMatch | None:
        if inp.face_bgr is None or not self.face.is_available():
            return None
        try:
            return self.face.identify(uid, inp.face_bgr)
        except ValueError:
            return None

    def _try_voice(self, uid: str, inp: TurnInput) -> VoiceMatch | None:
        if inp.voice_wav is None or not self.voice.is_available():
            return None
        try:
            return self.voice.identify(uid, inp.voice_wav, inp.sample_rate)
        except Exception:
            return None

    def _try_voice_emotion(self, inp: TurnInput) -> VoiceEmotion | None:
        """优先 emotion2vec SER；不可用时能量特征兜底 [S30]。"""
        if inp.voice_wav is None or inp.voice_wav.size == 0:
            return None
        ser = self.voice_emo.infer(inp.voice_wav, inp.sample_rate)
        if ser is not None:
            return ser
        # 能量特征兜底（粗估）
        wav = inp.voice_wav
        rms = float(np.sqrt(np.mean(wav ** 2)))
        zcr = float(np.mean(np.abs(np.diff(np.sign(wav))) > 0))
        arousal = min(1.0, rms * 4.0)
        label = "neutral"
        valence = 0.0
        if zcr > 0.35 and arousal > 0.5:
            label, valence = "angry", -0.5
        elif arousal < 0.15:
            label, valence = "sad", -0.2
        return VoiceEmotion(label, valence, arousal)

    def _crisis_reply(self, text: str) -> str:
        s = get_settings()
        return (
            "听到你这么说我很心疼。你此刻的感受很重要，但你不必一个人扛着。"
            f"请考虑现在联系专业援助：{s.crisis_hotline_zh}。"
            "如果你愿意，可以和我说说发生了什么，我会一直在这里听。")

    def _remember(self, uid: str, inp: TurnInput, reply: str, emotion: EmotionState):
        self._working[uid].append(TurnRecord(
            user_text=inp.text, assistant_text=reply,
            emotion=emotion.label, valence=emotion.valence, ts=time.time()))
