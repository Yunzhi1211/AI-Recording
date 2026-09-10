# -*- coding: utf-8 -*-
"""Local SQLite store for finished lessons."""
from __future__ import annotations

import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
DB_PATH = ASSETS / "studio.db"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    old = ROOT / "studio.db"
    if not DB_PATH.is_file() and old.is_file():
        try:
            shutil.move(str(old), str(DB_PATH))
        except OSError:
            pass
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS works (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                ppt_path TEXT,
                script_path TEXT,
                audio_path TEXT,
                video_path TEXT,
                slide_count INTEGER DEFAULT 0,
                notes TEXT DEFAULT '',
                status TEXT DEFAULT 'draft',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    init_posts()


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def upsert_work(payload: dict[str, Any]) -> int:
    init_db()
    title = (payload.get("title") or "未命名课件").strip()
    ppt = payload.get("ppt_path") or ""
    video = payload.get("video_path") or ""
    with connect() as conn:
        row = None
        if video:
            row = conn.execute(
                "SELECT id FROM works WHERE video_path = ? ORDER BY id DESC LIMIT 1",
                (video,),
            ).fetchone()
        if row is None and ppt:
            row = conn.execute(
                "SELECT id FROM works WHERE ppt_path = ? AND ifnull(video_path,'') = '' ORDER BY id DESC LIMIT 1",
                (ppt,),
            ).fetchone()
        fields = {
            "title": title,
            "ppt_path": ppt,
            "script_path": payload.get("script_path") or "",
            "audio_path": payload.get("audio_path") or "",
            "video_path": video,
            "slide_count": int(payload.get("slide_count") or 0),
            "notes": payload.get("notes") if payload.get("notes") is not None else None,
            "status": payload.get("status") or "draft",
            "updated_at": _now(),
        }
        if row:
            sets = ["title=?", "ppt_path=?", "script_path=?", "audio_path=?", "video_path=?", "slide_count=?", "status=?", "updated_at=?"]
            args: list[Any] = [
                fields["title"],
                fields["ppt_path"],
                fields["script_path"],
                fields["audio_path"],
                fields["video_path"],
                fields["slide_count"],
                fields["status"],
                fields["updated_at"],
            ]
            if fields["notes"] is not None:
                sets.append("notes=?")
                args.append(fields["notes"])
            args.append(row["id"])
            conn.execute(f"UPDATE works SET {', '.join(sets)} WHERE id=?", args)
            conn.commit()
            return int(row["id"])
        notes = fields["notes"] if fields["notes"] is not None else ""
        cur = conn.execute(
            """
            INSERT INTO works (title, ppt_path, script_path, audio_path, video_path, slide_count, notes, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fields["title"],
                fields["ppt_path"],
                fields["script_path"],
                fields["audio_path"],
                fields["video_path"],
                fields["slide_count"],
                notes,
                fields["status"],
                _now(),
                fields["updated_at"],
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_works() -> list[dict[str, Any]]:
    init_db()
    with connect() as conn:
        rows = conn.execute("SELECT * FROM works ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]


def get_work(work_id: int) -> dict[str, Any] | None:
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT * FROM works WHERE id=?", (work_id,)).fetchone()
        return dict(row) if row else None


def save_notes(work_id: int, notes: str) -> None:
    init_db()
    with connect() as conn:
        conn.execute(
            "UPDATE works SET notes=?, updated_at=? WHERE id=?",
            (notes, _now(), work_id),
        )
        conn.commit()


def delete_work(work_id: int) -> None:
    init_db()
    with connect() as conn:
        conn.execute("DELETE FROM works WHERE id=?", (work_id,))
        conn.commit()


def init_posts() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_id INTEGER,
                title TEXT NOT NULL,
                field TEXT DEFAULT '',
                body TEXT DEFAULT '',
                video_path TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        cols = {row[1] for row in conn.execute("PRAGMA table_info(posts)").fetchall()}
        for name, spec in (
            ("title_en", "TEXT DEFAULT ''"),
            ("body_en", "TEXT DEFAULT ''"),
            ("is_sample", "INTEGER DEFAULT 0"),
        ):
            if name not in cols:
                conn.execute(f"ALTER TABLE posts ADD COLUMN {name} {spec}")
        conn.commit()
    seed_sample_posts()


def seed_sample_posts() -> None:
    with connect() as conn:
        n = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        if n:
            return
        samples = [
            (
                "school",
                "先问家里有没有宠物，再翻到第二页",
                "Ask who has a pet at home, then turn to page two",
                "我不会一上来念稿。先举手：谁家里有猫或狗。有人举了，再问它最让你操心的一件事。这一问会把「为什么现在讲」变成他们自己的事。容易混的地方我放在第 4 页单独停：责任不是买零食，是每天要做的那几件小事。课后作业只要三句话，不要写作文。",
                "I do not start by reading. Hands up: who has a cat or a dog at home. Then one worry about that animal. Page 4 is where we stop: care is not treats, it is the small jobs every day. Homework is three sentences, not an essay.",
            ),
            (
                "corp",
                "培训别从目录念，从上周事故讲",
                "Do not open with the agenda. Open with last week’s incident",
                "开场 90 秒只讲一件真事：上周谁在哪一步漏了。三个要点各配一个能当场做的动作，不要再加第四个。中间我故意留 20 秒安静，让他们在本子上写「我回去先改哪一步」。收束时只留一个动作，方便下周抽查。",
                "The first 90 seconds are one real incident: who missed which step last week. Three points, each with one action they can do today. I leave twenty seconds of quiet for them to write the step they will change. We close on one action so next week’s check is easy.",
            ),
            (
                "personal",
                "自己看的片子，也要写卡在哪",
                "Even a film for yourself should name the stuck point",
                "我给自己做片时，会在第 3 页写一句「我上次就是在这里放弃的」。口播比幻灯片少一句也没关系，最后一页跟着倒数第二句走。看完当天用三句话记下来，不然过两天只记得自己做了视频。",
                "When I make a film for myself, page 3 says where I quit last time. It is fine if the voice has one fewer line than the slides — the last page shares the line before it. I write three sentences the same day, or in two days I only remember that a video exists.",
            ),
        ]
        now = _now()
        for field, title, title_en, body, body_en in samples:
            conn.execute(
                """
                INSERT INTO posts (work_id, title, field, body, video_path, created_at, title_en, body_en, is_sample)
                VALUES (NULL, ?, ?, ?, '', ?, ?, ?, 1)
                """,
                (title, field, body, now, title_en, body_en),
            )
        conn.commit()


def add_post(payload: dict[str, Any]) -> int:
    init_posts()
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO posts (work_id, title, field, body, video_path, created_at, title_en, body_en, is_sample)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                payload.get("work_id"),
                (payload.get("title") or "未命名").strip(),
                (payload.get("field") or "").strip(),
                payload.get("body") or "",
                payload.get("video_path") or "",
                _now(),
                (payload.get("title_en") or "").strip(),
                payload.get("body_en") or "",
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_posts(field: str | None = None) -> list[dict[str, Any]]:
    init_posts()
    with connect() as conn:
        if field:
            rows = conn.execute(
                "SELECT * FROM posts WHERE field = ? ORDER BY is_sample ASC, id DESC",
                (field,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM posts ORDER BY is_sample ASC, id DESC").fetchall()
        return [dict(r) for r in rows]


def get_post(post_id: int) -> dict[str, Any] | None:
    init_posts()
    with connect() as conn:
        row = conn.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        return dict(row) if row else None


def delete_post(post_id: int) -> None:
    init_posts()
    with connect() as conn:
        conn.execute("DELETE FROM posts WHERE id=?", (post_id,))
        conn.commit()
