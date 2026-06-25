"""db.py — AI日报助手的本地 SQLite 存储层。

隐私承诺："截图分析后即删"——数据库里**永不**保存截图路径或图片，
只保存 AI 对截图的文字描述（description）。screenshots/ 目录里的图片
是"待分析"的临时文件，analyze.py 分析完就删除。

两表：
  samples  一条 = 一次工作轨迹采样
  reports  一条 = 生成过的一份报告

所有数据仅存本地（默认 ~/.ai-daily/ai_daily.db），不上传。

被其他脚本复用：capture.sh 写 samples，analyze.py 回填 description，
aggregate.py 读 samples，SKILL.md 里生成报告时写 reports。
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATA_DIR = Path(os.environ.get("AI_DAILY_DIR") or (Path.home() / ".ai-daily"))
DB_PATH = DATA_DIR / "ai_daily.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS samples (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,          -- ISO8601 UTC，如 2026-06-24T10:53:11Z
    app           TEXT NOT NULL,          -- 前台应用名，如 "Code"；idle 时为 "—"
    title         TEXT DEFAULT '',        -- 窗口标题，可能为空
    description   TEXT DEFAULT '',        -- AI 对截图的文字描述（截图已删）
    shot_taken    INTEGER DEFAULT 0,      -- 1=当时截了图，0=隐私模式/无权限/idle
    analyzed      INTEGER DEFAULT 0,      -- 0=截图待分析，1=已分析(或无需分析)
    status        TEXT DEFAULT 'active',   -- active=活跃 / idle=空闲(≥阈值或屏保)
    category      TEXT DEFAULT 'work'      -- work/communication/distraction/personal/idle（见 classify.py）
);

CREATE TABLE IF NOT EXISTS reports (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    kind          TEXT NOT NULL,          -- daily / weekly / monthly
    period        TEXT NOT NULL,          -- 如 2026-06-24 或 2026-06-24~2026-06-30
    path          TEXT NOT NULL,          -- 生成的 HTML 文件绝对路径
    created_at    TEXT NOT NULL           -- 生成时间 ISO8601 UTC
);

CREATE INDEX IF NOT EXISTS idx_samples_ts ON samples(ts);
"""


def ensure_dirs() -> None:
    """创建数据目录与截图临时目录。screenshots/ 只放"待分析"的图。"""
    (DATA_DIR / "screenshots").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "reports").mkdir(parents=True, exist_ok=True)


@contextmanager
def connect():
    """打开一个连接，自动建表、提交、关闭。

    作为上下文管理器用：
        with db.connect() as c:
            c.execute("INSERT ...", (...))
    退出时自动 commit。
    """
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_sample(ts: str, app: str, title: str = "", shot_taken: bool = False,
                  status: str = "active", category: str = "work") -> int:
    """插入一条采样。

    返回新行的 id，供 analyze.py 回填 description 时定位。
    没截图的样本直接标 analyzed=1（无需分析），让 aggregate 立即可用。
    status: active=活跃在工作 / idle=空闲(≥阈值或屏保运行)。
    category: work/communication/distraction/personal/idle（见 classify.py）。
    """
    with connect() as c:
        cur = c.execute(
            "INSERT INTO samples (ts, app, title, description, shot_taken, analyzed, status, category) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (ts, app, title, "", 1 if shot_taken else 0, 0 if shot_taken else 1, status, category),
        )
        return cur.lastrowid


def pending_shots() -> list[sqlite3.Row]:
    """返回所有"截了图但还没分析"的样本（analyzed=0 且 shot_taken=1）。

    analyze.py 用它找出待分析的截图文件。
    """
    with connect() as c:
        return c.execute(
            "SELECT id, ts, app, title FROM samples WHERE analyzed=0 AND shot_taken=1 "
            "ORDER BY ts"
        ).fetchall()


def set_description(sample_id: int, description: str) -> None:
    """回填一条样本的 AI 描述，并标记为已分析。analyze.py 分析完图后调用。"""
    with connect() as c:
        c.execute(
            "UPDATE samples SET description=?, analyzed=1 WHERE id=?",
            (description, sample_id),
        )


def insert_report(kind: str, period: str, path: str) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO reports (kind, period, path, created_at) VALUES (?,?,?,?)",
            (kind, period, str(path), _now_utc()),
        )


def _now_utc() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cli(argv: list[str]) -> int:
    """供 shell 脚本调用的薄 CLI。完整逻辑请直接 import 本模块。

    子命令:
      (无)                 初始化/检查数据库
      _insert TS APP TITLE SHOT_TAKED   插入样本，回显新 id（capture.sh 用）
      _set_no_shot ID      把某条样本的 shot_taken 改成 0（截图失败时）
    """
    if not argv:
        ensure_dirs()
        with connect() as c:
            n = c.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
            r = c.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        print(f"数据库就绪：{DB_PATH}")
        print(f"  samples: {n} 条 | reports: {r} 条")
        return 0

    cmd = argv[0]
    if cmd == "_insert":
        # _insert TS APP TITLE SHOT_TAKEN STATUS CATEGORY
        ts, app, title, shot = argv[1], argv[2], argv[3], argv[4]
        status = argv[5] if len(argv) > 5 else "active"
        category = argv[6] if len(argv) > 6 else "work"
        sid = insert_sample(ts, app, title, shot_taken=(shot == "1"), status=status, category=category)
        print(sid)  # 只回显 id，capture.sh 依赖这个 stdout
        return 0
    if cmd == "_set_no_shot":
        with connect() as c:
            c.execute("UPDATE samples SET shot_taken=0, analyzed=1 WHERE id=?", (argv[1],))
        return 0
    raise SystemExit(f"db.py: 未知子命令 {cmd}")


if __name__ == "__main__":
    import sys
    raise SystemExit(_cli(sys.argv[1:]))
