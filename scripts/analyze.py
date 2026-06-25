#!/usr/bin/env python3
"""analyze.py — 截图分析协调器：把"待分析截图"交给 AI，回填文字描述，删图。

隐私核心：**截图分析后即删**。本脚本负责"登记待分析的图"和"接收描述后删图"，
真正"看图说话"由加载本 skill 的 AI 引擎完成（它才有视觉能力）。

两段式工作流（由 SKILL.md 里的 Agent 编排）：
  1. analyze.py --list
     → 打印所有待分析截图：id | 路径 | app | title | ts
     → Agent 用视觉模型逐张读图，产出一句"在做什么"的描述。
  2. analyze.py _set <id> <description>
     → 把描述写回 SQLite，并**立即删除该截图文件**（rm，不可恢复）。

为什么不在 watch 期间分析：watch 阶段没有 AI 在场。截图先暂存 screenshots/，
等用户要日报时（Agent 在场）统一分析+删除。暂存期由用户掌控，且可随时清空。

用法:
  ./analyze.py --list                 # 列出待分析（Agent 第 1 步）
  ./analyze.py _set 42 "在编辑日报模板"  # 存描述并删图（Agent 第 2 步，逐张调）
  ./analyze.py --purge                # 不经分析直接删除所有暂存截图（放弃分析）
"""
from __future__ import annotations

import sys
from pathlib import Path

import db

SHOTS_DIR = db.DATA_DIR / "screenshots"


def _shot_files(sample_id: int) -> list[Path]:
    """返回某样本的所有暂存截图。多屏：<id>.d1.png, <id>.d2.png；兼容旧 <id>.png。"""
    files = sorted(SHOTS_DIR.glob(f"{sample_id}.d*.png"))
    legacy = SHOTS_DIR / f"{sample_id}.png"
    if legacy.exists():
        files.append(legacy)
    return files


def list_pending() -> int:
    rows = db.pending_shots()
    if not rows:
        print("（没有待分析的截图）")
        return 0
    print(f"待分析截图 {len(rows)} 个样本：")
    for r in rows:
        files = _shot_files(r["id"])
        tag = f"{len(files)} 块屏" if files else "✗(文件缺失)"
        print(f"id={r['id']} | {tag} | {[str(p.name) for p in files]}")
        print(f"   app={r['app']} | title={r['title'] or '—'} | ts={r['ts']}")
    print()
    print("对每个样本的所有截图，用你的视觉能力读图后执行：")
    print("  python3 analyze.py _set <id> \"一句话描述在做什么\"")
    return 0


def set_description(sample_id: int, description: str) -> int:
    db.set_description(sample_id, description)
    files = _shot_files(sample_id)
    deleted = 0
    for p in files:
        p.unlink()
        deleted += 1
    print(f"id={sample_id}: 已存描述并删除 {deleted} 张截图")
    print(f"  描述：{description}")
    return 0


def purge() -> int:
    """放弃分析，直接清空所有暂存截图，并把对应样本标记为已分析（无描述）。"""
    rows = db.pending_shots()
    n = 0
    for r in rows:
        for p in _shot_files(r["id"]):
            p.unlink()
            n += 1
    # 把这些样本标记已分析（描述留空），让 aggregate 能放行
    with db.connect() as c:
        c.execute("UPDATE samples SET analyzed=1 WHERE analyzed=0")
    print(f"已清空 {n} 张暂存截图（未生成描述）。")
    return 0


def main(argv: list[str]) -> int:
    if not argv or argv[0] == "--list":
        return list_pending()
    if argv[0] == "_set":
        if len(argv) < 3:
            print("用法: analyze.py _set <id> <description>", file=sys.stderr)
            return 2
        return set_description(int(argv[1]), argv[2])
    if argv[0] == "--purge":
        return purge()
    print(f"analyze.py: 未知参数 {argv[0]}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
