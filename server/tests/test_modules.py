"""情绪融合 + 主动智能 + 身份融合单元测试。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from soulsync.agent.proactive import ProactiveCandidate, ProactiveEngine  # noqa: E402
from soulsync.emotion.fusion import (  # noqa: E402
    EmotionFusion, TextEmotion, VoiceEmotion)
from soulsync.memory.store import MemoryEntry, MemoryStore  # noqa: E402
from soulsync.perception.face import FaceMatch  # noqa: E402
from soulsync.perception.fuse import IdentityResolver  # noqa: E402
from soulsync.perception.voice import VoiceMatch  # noqa: E402


# ---------- 情绪融合 ----------

@pytest.fixture
def fusion():
    return EmotionFusion(crisis_keywords=("自杀", "不想活", "kill myself"))


def test_fusion_agree(fusion):
    s = fusion.fuse(TextEmotion("sad", -0.6), VoiceEmotion("sad", -0.5, 0.3))
    assert s.label == "sad" and s.source == "fused"


def test_fusion_conflict_voice_wins(fusion):
    s = fusion.fuse(TextEmotion("happy", 0.7), VoiceEmotion("angry", -0.7, 0.85))
    assert s.label == "angry"


def test_fusion_single_side(fusion):
    assert fusion.fuse(TextEmotion("happy", 0.7), None).source == "text"
    assert fusion.fuse(None, VoiceEmotion("sad", -0.6, 0.2)).source == "voice"
    assert fusion.fuse(None, None).source == "none"


def test_crisis_detection(fusion):
    assert fusion.detect_crisis("我不想活了")
    assert fusion.detect_crisis("I want to kill myself")
    assert not fusion.detect_crisis("今天天气不错")
    s = fusion.fuse(TextEmotion("sad", -0.9, crisis=True), None)
    assert s.crisis


# ---------- 主动智能 ----------

@pytest.fixture
def proactive(tmp_path):
    store = MemoryStore(tmp_path / "t.db", embed_dim=8)
    yield ProactiveEngine(store), store
    store.close()


def test_proactive_emotion_trigger(proactive):
    eng, store = proactive
    assert not eng.evaluate("u1").should_speak  # 无信号
    for txt, val in [("被领导批评了", -0.7), ("失眠很严重", -0.6), ("压力大", -0.5)]:
        store.add_memory(MemoryEntry(None, "u1", "episodic", txt, 0.8, valence=val))
    d = eng.evaluate("u1")
    assert d.should_speak and d.candidate.trigger == "emotion"


def test_proactive_min_gap(proactive):
    eng, store = proactive
    store.add_memory(MemoryEntry(None, "u1", "episodic", "低落", 0.8, valence=-0.7))
    store.add_memory(MemoryEntry(None, "u1", "episodic", "难过", 0.8, valence=-0.6))
    d = eng.evaluate("u1")
    assert d.should_speak
    eng.log_proactive("u1", d.candidate, "还好吗")
    assert not eng.evaluate("u1").should_speak  # 间隔闸门


def test_proactive_negative_backoff(proactive):
    eng, store = proactive
    eng.log_proactive("u1", ProactiveCandidate("time", 0.9, "t"), "m1")
    eng.log_reaction("u1", "negative")
    eng.log_proactive("u1", ProactiveCandidate("time", 0.9, "t"), "m2")
    eng.log_reaction("u1", "negative")
    eng.log_proactive("u1", ProactiveCandidate("time", 0.9, "t"), "m3")
    eng.log_reaction("u1", "negative")
    d = eng.evaluate("u1", now=time.time() + 9000)
    assert not d.should_speak and d.cooldown_until is not None


def test_proactive_daily_cap(proactive):
    eng, store = proactive
    base = time.time() - 60
    for i in range(eng.daily_cap + 2):
        store.conn.execute(
            "INSERT INTO proactive_log (id,user_id,ts,trigger,score,message)"
            " VALUES (?,?,?,'time',0.9,'x')", (f"id{i}", "u1", base + i * 60))
    store.conn.commit()
    assert not eng.evaluate("u1", now=time.time() + 10000).should_speak


# ---------- 身份融合 ----------

@pytest.fixture
def resolver(tmp_path):
    store = MemoryStore(tmp_path / "t.db", embed_dim=8)
    yield IdentityResolver(store), store
    store.close()


def test_identity_full_flow(resolver):
    res, store = resolver
    face = FaceMatch("face_1", 0.82, is_new=False)
    voice = VoiceMatch("voice_1", 0.91, is_new=False)
    r1 = res.resolve("u1", face, voice)
    assert r1.identity_id == "face_1" and not r1.confirmed
    res._bump_cooccurrence("u1", "face_1", "voice_1")
    res._bump_cooccurrence("u1", "face_1", "voice_1")
    r2 = res.resolve("u1", face, voice)
    assert r2.confirmed  # 第 3 次共现转正
    res.set_name("u1", "face_1", "小邦")
    r3 = res.resolve("u1", face, None)
    assert r3.name == "小邦" and r3.confirmed
    r4 = res.resolve("u1", None, VoiceMatch("voice_1", 0.9, False))
    assert r4.identity_id == "voice_1"


def test_identity_stranger(resolver):
    res, _ = resolver
    r = res.resolve("u1", FaceMatch(None, 0.1, True), VoiceMatch(None, 0.2, True))
    assert r.is_new and r.identity_id is None
