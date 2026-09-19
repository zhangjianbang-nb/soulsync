"""后台任务：反思定时器 + 周期性遗忘衰减。

随 FastAPI lifespan 启动；对每个有活动的用户执行：
- 每 reflection_interval_minutes：跑 consolidate + reflect（夜间巩固 [S15][S4]）
- 每日：apply_decay（艾宾浩斯 [S3]）
"""
from __future__ import annotations

import asyncio
import logging
import time

from soulsync.config import get_settings

log = logging.getLogger("soulsync.background")


class BackgroundTasks:
    def __init__(self, agent):
        self.agent = agent
        self._task: asyncio.Task | None = None
        self._stopped = asyncio.Event()

    def start(self):
        self._task = asyncio.create_task(self._loop(), name="soulsync-bg")

    async def stop(self):
        self._stopped.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self):
        s = get_settings()
        interval = max(60, s.reflection_interval_minutes * 60)
        last_decay_day = -1
        while not self._stopped.is_set():
            try:
                await asyncio.wait_for(self._stopped.wait(), timeout=interval)
                break  # stopped
            except asyncio.TimeoutError:
                pass
            try:
                await self._run_once()
            except Exception:
                log.exception("background task cycle failed")
            # 每日衰减（跨天触发一次）
            today = int(time.time() // 86400)
            if today != last_decay_day:
                last_decay_day = today
                try:
                    self._decay_all()
                except Exception:
                    log.exception("daily decay failed")

    async def _run_once(self):
        """对所有有记忆的用户跑巩固+反思。"""
        conn = self.agent.store.conn
        uids = [r["user_id"] for r in conn.execute(
            "SELECT DISTINCT user_id FROM memories").fetchall()]
        for uid in uids:
            n = await self.agent.reflector.consolidate(uid)
            if n:
                log.info("consolidated %d memories for %s", n, uid)
            await self.agent.reflector.reflect(uid)

    def _decay_all(self):
        conn = self.agent.store.conn
        uids = [r["user_id"] for r in conn.execute(
            "SELECT DISTINCT user_id FROM memories").fetchall()]
        for uid in uids:
            self.agent.store.apply_decay(uid)
