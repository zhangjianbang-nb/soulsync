"""SoulSync 服务端入口：uvicorn soulsync.main:app --host 0.0.0.0 --port 8800"""
from __future__ import annotations

from fastapi import FastAPI

from soulsync.api.routes import make_router
from soulsync.config import get_settings
from soulsync.memory.store import MemoryStore


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="SoulSync", version="0.2.0",
                  description="Multimodal emotional companion agent")
    store = MemoryStore(s.db_path, embed_dim=s.embed_dim)
    app.state.store = store

    # Agent 惰性构造（感知模型重，首次 chat 时加载）
    from soulsync.agent.core import CompanionAgent
    agent = CompanionAgent(store)
    app.state.agent = agent

    # 后台任务（反思定时器 + 每日遗忘衰减）
    from soulsync.agent.background import BackgroundTasks
    bg = BackgroundTasks(agent)
    app.state.background = bg

    app.include_router(make_router(agent))

    @app.on_event("startup")
    async def _start():
        bg.start()

    @app.on_event("shutdown")
    async def _shutdown():
        await bg.stop()
        store.close()

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    s = get_settings()
    uvicorn.run(app, host=s.server_host, port=s.server_port)
