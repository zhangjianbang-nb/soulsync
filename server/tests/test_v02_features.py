"""v0.2.0 新特性测试：SSE 流式 / 多轮上下文 / 后台任务。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from soulsync import config  # noqa: E402
from soulsync.main import create_app  # noqa: E402


class StreamingMockLLM:
    """支持 stream() 的 mock：把回复拆成多个增量。"""

    async def complete(self, prompt, **kw):
        history = kw.get("history")
        if history is not None and kw.get("_probe_history"):
            return f"history_len={len(history)}"
        return "好的我在呢"

    async def stream(self, prompt, **kw):
        for piece in ["好的", "我在", "呢"]:
            yield piece


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SOULSYNC_DATA_DIR", str(tmp_path / "data"))
    config._settings = None
    application = create_app()
    application.state.agent.llm = StreamingMockLLM()
    application.state.agent.reflector.llm = application.state.agent.llm
    return application


def parse_sse(text: str) -> list[dict]:
    events = []
    for line in text.split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


@pytest.mark.asyncio
async def test_sse_stream_events(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/v1/chat/stream", json={"user_id": "s1", "text": "在吗"})
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
        events = parse_sse(r.text)
        types = [e["type"] for e in events]
        assert types[0] == "meta"
        assert "delta" in types
        assert types[-1] == "done"
        # delta 拼起来等于完整回复
        reply = "".join(e["text"] for e in events if e["type"] == "delta")
        assert reply == "好的我在呢"
        done = [e for e in events if e["type"] == "done"][0]
        assert done["reply"] == "好的我在呢"


@pytest.mark.asyncio
async def test_multiturn_history_grows(app):
    """两轮对话后，第二轮的 working memory 应包含第一轮。"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        await c.post("/v1/chat", json={"user_id": "s2", "text": "第一句"})
        agent = app.state.agent
        wm = list(agent._working["s2"])
        assert len(wm) == 1
        assert wm[0].user_text == "第一句" and wm[0].assistant_text == "好的我在呢"
        history = agent._build_history("s2")
        # 单轮工作记忆时 history 为空（去掉最后半轮）
        assert history == []
        # 第二轮后 history 含第一轮
        await c.post("/v1/chat", json={"user_id": "s2", "text": "第二句"})
        history2 = agent._build_history("s2")
        assert len(history2) == 2
        assert history2[0] == {"role": "user", "content": "第一句"}
        assert history2[1] == {"role": "assistant", "content": "好的我在呢"}


@pytest.mark.asyncio
async def test_background_tasks_cycle(app):
    """后台任务单次循环可跑（consolidate+reflect 对空用户安全）。"""
    bg = app.state.background
    await bg._run_once()  # 无用户时不抛异常
    bg._decay_all()


@pytest.mark.asyncio
async def test_health_reports_version(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/v1/health")
        assert r.status_code == 200
