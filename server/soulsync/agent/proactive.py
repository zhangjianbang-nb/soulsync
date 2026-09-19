"""主动智能引擎（M7）：

- 内心独白门控 [S38]：内部评估介入冲动分数，超阈值才主动
- 三类触发源 [S35]：时间（cron 式问候）/ 事件（沉默 N 天、生日）/ 情绪（连续低 valence）
- 信任反馈 [S37]：用户负面回应 → 连续 N 次负面则冷却降频
- 每日上限防骚扰 [S51]：克制频率
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from soulsync.config import get_settings
from soulsync.memory.store import MemoryStore


@dataclass
class ProactiveCandidate:
    trigger: str          # time | event | emotion
    score: float          # 0-1 介入冲动
    reason: str
    memory_refs: list[str] = field(default_factory=list)


@dataclass
class ProactiveDecision:
    should_speak: bool
    candidate: ProactiveCandidate | None
    cooldown_until: float | None = None


class ProactiveEngine:
    def __init__(self, store: MemoryStore):
        self.store = store
        s = get_settings()
        self.threshold = s.proactive_score_threshold
        self.min_gap = s.proactive_min_gap_minutes * 60
        self.daily_cap = s.proactive_daily_cap
        self.negative_backoff = s.proactive_negative_backoff

    def evaluate(self, user_id: str, now: float | None = None) -> ProactiveDecision:
        """评估是否应主动开口。返回决策（分数+理由），由编排器生成消息内容。"""
        now = now or time.time()
        if not get_settings().proactive_enabled:
            return ProactiveDecision(False, None)

        # 硬闸门：间隔/每日上限/负面冷却 [S37][S51]
        last = self.store.conn.execute(
            "SELECT ts, user_reaction FROM proactive_log WHERE user_id=? "
            "ORDER BY ts DESC LIMIT 1", (user_id,)).fetchone()
        if last and now - last["ts"] < self.min_gap:
            return ProactiveDecision(False, None)
        today_start = now - (now % 86400)
        cnt = self.store.conn.execute(
            "SELECT COUNT(*) AS n FROM proactive_log WHERE user_id=? AND ts>?",
            (user_id, today_start)).fetchone()["n"]
        if cnt >= self.daily_cap:
            return ProactiveDecision(False, None)
        recent_neg = self.store.conn.execute(
            "SELECT user_reaction FROM proactive_log WHERE user_id=? "
            "ORDER BY ts DESC LIMIT ?", (user_id, self.negative_backoff)).fetchall()
        if (len(recent_neg) >= self.negative_backoff
                and all(r["user_reaction"] == "negative" for r in recent_neg)):
            # 连续负面：冷却一个 min_gap 周期
            return ProactiveDecision(False, None,
                                       cooldown_until=now + self.min_gap)

        best = self._best_candidate(user_id, now)
        if best and best.score >= self.threshold:
            return ProactiveDecision(True, best)
        return ProactiveDecision(False, best)

    def _best_candidate(self, user_id: str, now: float) -> ProactiveCandidate | None:
        cands: list[ProactiveCandidate] = []

        # 1) 情绪触发：近期连续负 valence → 关心 [S51 主动回访]
        rows = self.store.conn.execute(
            "SELECT valence, content, id FROM memories WHERE user_id=? AND layer='episodic' "
            "AND valence IS NOT NULL ORDER BY created_at DESC LIMIT 3",
            (user_id,)).fetchall()
        if len(rows) >= 2 and all((r["valence"] or 0) < -0.3 for r in rows):
            score = 0.55 + 0.15 * min(3, len(rows))
            cands.append(ProactiveCandidate(
                "emotion", min(score, 0.95),
                reason="用户近期情绪持续低落",
                memory_refs=[r["id"] for r in rows[:2]]))

        # 2) 事件触发：沉默 3 天
        last_msg = self.store.conn.execute(
            "SELECT MAX(created_at) AS t FROM memories WHERE user_id=?", (user_id,)).fetchone()
        silence_days = (now - (last_msg["t"] or now)) / 86400.0 if last_msg else 0
        if silence_days >= 3.0:
            cands.append(ProactiveCandidate(
                "event", min(0.5 + 0.1 * silence_days, 0.9),
                reason=f"已沉默 {silence_days:.1f} 天"))

        # 3) 时间触发：早/晚安（分数低，靠阈值兜底）
        hour = (now % 86400) / 3600.0
        if 7.5 <= hour <= 10.0:
            cands.append(ProactiveCandidate("time", 0.45, reason="早安问候窗口"))
        elif 21.5 <= hour <= 23.0:
            cands.append(ProactiveCandidate("time", 0.4, reason="晚安窗口"))

        if not cands:
            return None
        cands.sort(key=lambda c: c.score, reverse=True)
        return cands[0]

    def log_proactive(self, user_id: str, cand: ProactiveCandidate, message: str):
        self.store.conn.execute(
            "INSERT INTO proactive_log (id,user_id,ts,trigger,score,message,user_reaction)"
            " VALUES (?,?,?,?,?,?,NULL)",
            (uuid.uuid4().hex[:16], user_id, time.time(), cand.trigger, cand.score, message))
        self.store.conn.commit()

    def log_reaction(self, user_id: str, reaction: str):
        """用户对最近一次主动消息的回应（positive/neutral/negative）。"""
        row = self.store.conn.execute(
            "SELECT id FROM proactive_log WHERE user_id=? ORDER BY ts DESC LIMIT 1",
            (user_id,)).fetchone()
        if row:
            self.store.conn.execute(
                "UPDATE proactive_log SET user_reaction=? WHERE id=?",
                (reaction, row["id"]))
            self.store.conn.commit()
