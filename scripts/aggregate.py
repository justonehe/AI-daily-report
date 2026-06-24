#!/usr/bin/env python3
"""aggregate.py — 从 SQLite 聚合工作轨迹，产出喂给 AI 的"素材"（Markdown）。

读取按时间过滤后的 samples，做两件事：
  1) 计算每个 App 的停留时长估计（相邻样本时间差的中点法）。
  2) 按时间顺序列"活动条目"，含时间、App、窗口标题、**AI 截图描述**。

这段 Markdown 是"原始素材"，不是最终日报——由 Agent 套 HTML 模板、把条目
推理成工作事项后生成正式报告。

前置条件：建议先跑 analyze.py 把待分析截图处理掉（分析+删除）。
未分析的样本也会显示，但 description 为空（Agent 会看到提示）。

为什么停留时长用中点法而不是"采样间隔": 只知道"某时刻用户在用 X"，不知何时切走。
中点法（相邻样本时长对半分）对采样间隔不敏感，且免费处理边界。

用法:
  ./aggregate.py                       # 今天
  ./aggregate.py --day 2026-06-24
  ./aggregate.py --week                # 本周（周一至今）
  ./aggregate.py --month               # 本月（1 日至今）
  ./aggregate.py --from 2026-06-20 --to 2026-06-24
  ./aggregate.py --json                # 同数据以 JSON 输出（便于 Agent 程序化消费）
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path

import db


# --------------------------------------------------------------------------- #
# 日期范围
# --------------------------------------------------------------------------- #
def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def resolve_range(kind: str, day: str | None, dfrom: str | None, dto: str | None) -> tuple[date, date]:
    today = date.today()
    if dfrom and dto:
        return _parse_day(dfrom), _parse_day(dto)
    if kind == "week":
        return _monday(today), today
    if kind == "month":
        return today.replace(day=1), today
    d = _parse_day(day) if day else today
    return d, d


def _parse_day(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


# --------------------------------------------------------------------------- #
# 读取样本（SQLite）
# --------------------------------------------------------------------------- #
@dataclass
class Sample:
    dt: datetime
    app: str
    title: str
    description: str


def load_samples(start: date, end: date) -> list[Sample]:
    tz = datetime.now().astimezone().tzinfo
    start_local = datetime.combine(start, datetime.min.time(), tzinfo=tz)
    end_local = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=tz)
    out: list[Sample] = []
    with db.connect() as c:
        rows = c.execute(
            "SELECT ts, app, title, description FROM samples ORDER BY ts"
        ).fetchall()
    for r in rows:
        try:
            dt = datetime.fromisoformat(r["ts"].replace("Z", "+00:00")).astimezone(tz)
        except ValueError:
            continue
        if not (start_local <= dt < end_local):
            continue
        out.append(Sample(dt, r["app"] or "Unknown", (r["title"] or "").strip(),
                          (r["description"] or "").strip()))
    return out


# --------------------------------------------------------------------------- #
# 聚合
# --------------------------------------------------------------------------- #
def dwell_times(samples: list[Sample]) -> dict[str, float]:
    """中点法估算每个 App 停留秒数。最后一样本无下文，记 0。"""
    if not samples:
        return {}
    secs: dict[str, float] = {}
    for key, val in _dwell_pairs(samples):
        secs[key] = secs.get(key, 0.0) + val
    return secs


def _dwell_pairs(samples: list[Sample]):
    """yield (app, seconds)：相邻样本时长对半分给前后两个 App。"""
    for i, s in enumerate(samples[:-1]):
        gap = (samples[i + 1].dt - s.dt).total_seconds()
        if gap <= 0:
            continue
        yield (s.app, gap / 2.0)
        yield (samples[i + 1].app, gap / 2.0)


def fmt_duration(sec: float) -> str:
    if sec < 60:
        return f"{int(sec)}s"
    m = int(round(sec / 60))
    if m < 60:
        return f"{m}min"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m" if m else f"{h}h"


# --------------------------------------------------------------------------- #
# 渲染
# --------------------------------------------------------------------------- #
def render(samples: list[Sample], start: date, end: date) -> str:
    lines: list[str] = []
    head = f"{start.isoformat()}" if start == end else f"{start.isoformat()} ~ {end.isoformat()}"
    lines.append(f"# 工作轨迹素材（{head}）\n")

    if not samples:
        lines.append("> 该时间范围内没有采集到样本。")
        lines.append("> 可能原因：未运行 watch.sh / 当天没有记录 / 日期选错。")
        return "\n".join(lines)

    n_desc = sum(1 for s in samples if s.description)
    lines.append(f"- 采样时间跨度：{samples[0].dt:%H:%M} – {samples[-1].dt:%H:%M}（本地）")
    lines.append(f"- 样本数：{len(samples)}（其中 {n_desc} 条带 AI 截图描述）\n")

    secs = dwell_times(samples)
    lines.append("## 停留时长 Top\n")
    lines.append("| 应用 | 估计停留 |")
    lines.append("| --- | --- |")
    for app, sec in sorted(secs.items(), key=lambda kv: -kv[1])[:10]:
        lines.append(f"| {app} | {fmt_duration(sec)} |")
    lines.append("")

    lines.append("## 时间线\n")
    for s in samples:
        t = s.dt.strftime("%H:%M")
        desc = s.description or "（无截图描述）"
        lines.append(f"- **{t}** `{s.app}` — {s.title or '—'}")
        lines.append(f"  - {desc}")
    return "\n".join(lines) + "\n"


def render_json(samples: list[Sample], start: date, end: date) -> str:
    return json.dumps(
        {
            "range": {"start": start.isoformat(), "end": end.isoformat()},
            "summary": {
                "sample_count": len(samples),
                "with_description": sum(1 for s in samples if s.description),
                "dwell": {a: round(v) for a, v in sorted(
                    dwell_times(samples).items(), key=lambda kv: -kv[1])},
            },
            "timeline": [
                {"time": s.dt.strftime("%H:%M"), "app": s.app,
                 "title": s.title, "description": s.description}
                for s in samples
            ],
        },
        ensure_ascii=False, indent=2,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="聚合AI日报助手的工作轨迹样本。")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--day", help="某一天 YYYY-MM-DD")
    g.add_argument("--week", action="store_true", help="本周（周一至今）")
    g.add_argument("--month", action="store_true", help="本月（1 日至今）")
    p.add_argument("--from", dest="dfrom", help="起始日 YYYY-MM-DD")
    p.add_argument("--to", dest="dto", help="结束日 YYYY-MM-DD")
    p.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = p.parse_args(argv)

    if (args.dfrom is None) != (args.dto is None):
        p.error("--from 和 --to 必须同时给出")
    kind = "week" if args.week else "month" if args.month else "day"
    start, end = resolve_range(kind, args.day, args.dfrom, args.dto)
    samples = load_samples(start, end)
    out = render_json(samples, start, end) if args.json else render(samples, start, end)
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
