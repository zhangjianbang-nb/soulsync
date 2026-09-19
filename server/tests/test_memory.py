"""记忆存储层单元测试。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from soulsync.config import get_settings  # noqa: E402
from soulsync.memory.store import MemoryStore, MemoryEntry, cosine  # noqa: E402


@pytest.fixture
def store(tmp_path):
    s = MemoryStore(tmp_path / "t.db", embed_dim=8)
    yield s
    s.close()


VEC1 = [0.1, 0.9, 0.0, 0.0, 0, 0, 0, 0]
VEC2 = [0.9, 0.1, 0.0, 0.0, 0, 0, 0, 0]
VEC3 = [0.1, 0.0, 0.9, 0.0, 0, 0, 0, 0]


def test_add_and_retrieve(store):
    e1 = store.add_memory(MemoryEntry(None, "u1", "episodic", "用户今天感冒了", 0.8,
                                      emotion="sad", valence=-0.6), VEC1)
    e2 = store.add_memory(MemoryEntry(None, "u1", "episodic", "今天天气不错", 0.2), VEC2)
    e3 = store.add_memory(MemoryEntry(None, "u1", "semantic", "用户喜欢周末爬山", 0.7,
                                      emotion="joy", valence=0.7), VEC3)
    assert e1.id and e2.id and e3.id
    hits = store.search("u1", [0.1, 0.85, 0.0, 0.0, 0, 0, 0, 0], top_k=2)
    assert hits[0][0].id == e1.id


def test_profile_sensitive_isolation(store):
    store.set_profile("u1", "name", "小邦")
    store.set_profile("u1", "mental_state", "焦虑", sensitive=True)
    assert store.get_profile("u1") == {"name": "小邦"}
    prof = store.get_profile("u1", include_sensitive=True)
    assert prof["mental_state"] == "焦虑"


def test_decay_aging(store):
    import time as _t
    e_low = store.add_memory(MemoryEntry(None, "u1", "episodic", "琐碎", 0.2), VEC2)
    e_hi = store.add_memory(MemoryEntry(None, "u1", "episodic", "重要事件", 0.9), VEC1)
    old = _t.time() - 30 * 86400
    for e in (e_low, e_hi):
        store.conn.execute("UPDATE memories SET created_at=? WHERE id=?", (old, e.id))
    store.conn.commit()
    store.apply_decay("u1", half_life_days=14)
    d_low = store.conn.execute("SELECT decay FROM memories WHERE id=?", (e_low.id,)).fetchone()["decay"]
    d_hi = store.conn.execute("SELECT decay FROM memories WHERE id=?", (e_hi.id,)).fetchone()["decay"]
    assert d_low < d_hi


def test_consolidate_candidates(store):
    import time as _t
    e_old = store.add_memory(MemoryEntry(None, "u1", "episodic", "旧事件", 0.5), VEC1)
    store.add_memory(MemoryEntry(None, "u1", "episodic", "新事件", 0.5), VEC2)
    store.conn.execute("UPDATE memories SET created_at=? WHERE id=?",
                       (_t.time() - 7200, e_old.id))
    store.conn.commit()
    cands = store.consolidate_candidates("u1", older_than_hours=1)
    assert [c.id for c in cands] == [e_old.id]


def test_right_to_be_forgotten(store):
    store.set_profile("u1", "name", "小邦")
    store.add_memory(MemoryEntry(None, "u1", "episodic", "事件", 0.5), VEC1)
    assert store.delete_profile_key("u1", "name")
    store.forget_user("u1")
    assert store.list_memories("u1") == []
    assert store.get_profile("u1", include_sensitive=True) == {}


def test_cosine():
    assert cosine([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine([], [1.0]) == 0.0
    assert get_settings().memory_importance_gate > 0
