"""身份融合（M5）：人脸×声纹×名字 三重证据。

- 共现绑定 [工程惯例]：同一时间窗内人脸命中+声纹命中 → 绑定同一档案，N 次转正
- 名字：用户口头告知 → LLM 抽取 → 写画像；未确认身份统一称呼"你"
- 档案 id：face_xxx / voice_xxx 融合后的 identity_id
"""
from __future__ import annotations

from dataclasses import dataclass, field

from soulsync.config import get_settings
from soulsync.memory.store import MemoryStore
from soulsync.perception.face import FaceMatch
from soulsync.perception.voice import VoiceMatch


@dataclass
class ResolvedIdentity:
    identity_id: str | None = None    # 融合档案 id；None=陌生人
    name: str | None = None
    confirmed: bool = False           # 共现满 N 次
    face: FaceMatch | None = None
    voice: VoiceMatch | None = None
    is_new: bool = False


class IdentityResolver:
    def __init__(self, store: MemoryStore):
        self.store = store
        s = get_settings()
        self.cooccurrence_needed = s.identity_cooccurrence_needed

    def resolve(self, user_id: str, face: FaceMatch | None,
                voice: VoiceMatch | None) -> ResolvedIdentity:
        """给定本轮人脸/声纹匹配结果，解析出统一身份。"""
        out = ResolvedIdentity(face=face, voice=voice)
        face_id = face.identity_id if face else None
        voice_id = voice.identity_id if voice else None

        # 1) 双模态都有 → 走绑定逻辑
        if face_id and voice_id:
            if self._bound(user_id, face_id, voice_id):
                out.identity_id = face_id
                out.confirmed = True
                out.is_new = False
            else:
                # 共现计数+1，满 N 次绑定转正
                n = self._bump_cooccurrence(user_id, face_id, voice_id)
                out.identity_id = face_id
                out.confirmed = n >= self.cooccurrence_needed
                out.is_new = False
        elif face_id or voice_id:
            # 2) 单模态：找它绑定过的搭档身份
            partner = self._bound_partner(user_id, face_id or voice_id)
            out.identity_id = face_id or voice_id
            if partner:
                out.confirmed = True  # 已有绑定记录
        else:
            # 3) 全新陌生人：新建档案（等注册）
            out.is_new = True

        if out.identity_id:
            row = self.store.conn.execute(
                "SELECT name FROM identity_bindings WHERE user_id=? AND identity_id=?",
                (user_id, out.identity_id)).fetchone()
            out.name = row["name"] if row and row["name"] else None
            b = self.store.conn.execute(
                "SELECT confirmed FROM identity_bindings WHERE user_id=? AND identity_id=?",
                (user_id, out.identity_id)).fetchone()
            if b and b["confirmed"]:
                out.confirmed = True
        return out

    def set_name(self, user_id: str, identity_id: str, name: str):
        self.store.conn.execute(
            "INSERT INTO identity_bindings (user_id,identity_id,name,confirmed,cooccurrences,updated_at)"
            " VALUES (?,?,?,?,0,strftime('%s','now'))"
            " ON CONFLICT(user_id,identity_id) DO UPDATE SET name=excluded.name,"
            " updated_at=excluded.updated_at",
            (user_id, identity_id, name, 0))
        self.store.conn.commit()

    def _bound(self, user_id: str, face_id: str, voice_id: str) -> bool:
        row = self.store.conn.execute(
            "SELECT 1 FROM bindings_cross WHERE user_id=? AND face_id=? AND voice_id=?",
            (user_id, face_id, voice_id)).fetchone()
        return row is not None

    def _bump_cooccurrence(self, user_id: str, face_id: str, voice_id: str) -> int:
        self.store.conn.execute(
            "INSERT INTO bindings_cross (user_id,face_id,voice_id,count) VALUES (?,?,?,1)"
            " ON CONFLICT(user_id,face_id,voice_id) DO UPDATE SET count=count+1",
            (user_id, face_id, voice_id))
        self.store.conn.commit()
        row = self.store.conn.execute(
            "SELECT count FROM bindings_cross WHERE user_id=? AND face_id=? AND voice_id=?",
            (user_id, face_id, voice_id)).fetchone()
        return row["count"] if row else 0

    def _bound_partner(self, user_id: str, identity_id: str) -> str | None:
        row = self.store.conn.execute(
            "SELECT voice_id FROM bindings_cross WHERE user_id=? AND face_id=?",
            (user_id, identity_id)).fetchone()
        if row:
            return row["voice_id"]
        row = self.store.conn.execute(
            "SELECT face_id FROM bindings_cross WHERE user_id=? AND voice_id=?",
            (user_id, identity_id)).fetchone()
        return row["face_id"] if row else None
