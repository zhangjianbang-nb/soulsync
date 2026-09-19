"""端到端 API 测试：mock LLM 走完整 chat 流水线（记忆检索/身份/情绪/危机旁路/主动）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from soulsync import config  # noqa: E402
from soulsync.main import create_app  # noqa: E402


class MockLLM:
    async def complete(self, prompt, **kw):
        if "事实/事件/情绪" in prompt:
            return '[{"content": "用户感冒了", "importance": 8, "emotion": "sad", "valence": -0.5}]'
        if "合并去重" in prompt:
            return '[{"content": "合并记忆", "importance": 7, "source_ids": [1]}]'
        if "提炼" in prompt or "洞察" in prompt:
            return '[{"content": "用户最近压力大", "importance": 8}]'
        if "主动发一条" in prompt:
            return "这几天怎么样？还记得你上次说感冒了，好点了吗？"
        return "我在呢。你说说看，我最近发生了什么？"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SOULSYNC_DATA_DIR", str(tmp_path / "data"))
    config._settings = None  # 重置单例
    application = create_app()
    application.state.agent.llm = MockLLM()
    application.state.agent.reflector.llm = application.state.agent.llm
    return application


@pytest.mark.asyncio
async def test_chat_and_memory(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/v1/chat", json={"user_id": "u1", "text": "我今天感冒了，头疼"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["reply"] and body["turn_id"]
        assert body["emotion"]["label"] in ("neutral", "sad")
        assert body["crisis"] is False
        # 记忆可查
        r2 = await c.get("/v1/memories/u1")
        assert r2.status_code == 200


@pytest.mark.asyncio
async def test_crisis_bypass(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/v1/chat", json={"user_id": "u2", "text": "我不想活了"})
        body = r.json()
        assert body["crisis"] is True
        assert ("12356" in body["reply"]) or "心理援助" in body["reply"]


@pytest.mark.asyncio
async def test_profile_and_forget(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        await c.post("/v1/identity/name", json={"user_id": "u3", "identity_id": "f1", "name": "小邦"})
        r = await c.get("/v1/profile/u3")
        assert r.json().get("name") == "小邦"
        r2 = await c.delete("/v1/profile/u3/name")
        assert r2.status_code == 200
        r3 = await c.delete("/v1/user/u3")
        assert r3.status_code == 200


@pytest.mark.asyncio
async def test_proactive_flow(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/v1/proactive", json={"user_id": "u9"})
        assert r.status_code == 200
        # 无记忆时分数低 → 不主动（message 为 null 或字符串都合法）
        assert "message" in r.json()
