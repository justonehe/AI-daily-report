#!/usr/bin/env bash
# capture.sh — 采集一次工作轨迹样本
#
# 一次采样 = 一个时间戳 + 当前前台应用/窗口标题 +（可选）临时截图。
# 写入本地 SQLite（scripts/db.py），截图存到 screenshots/<id>.png 等 analyze.py
# 分析后删除——**数据库里永不保存图片路径，只保存 AI 文字描述**。
#
# 设计为"单次幂等动作"：watch.sh 循环调用它，也能单独触发。
#
# 用法:
#   ./capture.sh                       # 应用/窗口 + 临时截图（待 AI 分析后删）
#   AI_DAILY_NO_SHOT=1 ./capture.sh    # 只记应用/窗口，不截图
#
# 环境变量:
#   AI_DAILY_DIR     数据目录，默认 ~/.ai-daily
#   AI_DAILY_NO_SHOT 任何非空值 = 跳过截图（隐私模式 / 无屏权限时）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="python3"
DATA_DIR="${AI_DAILY_DIR:-$HOME/.ai-daily}"
NO_SHOT="${AI_DAILY_NO_SHOT:-}"
SHOTS_DIR="$DATA_DIR/screenshots"

mkdir -p "$SHOTS_DIR"

# --- 1. 取前台应用名 + 窗口标题 -------------------------------------------
app=""
title=""
if info=$(osascript -e 'tell application "System Events" to get {name of first application process whose frontmost is true, title of (first window of (first application process whose frontmost is true))}' 2>/dev/null); then
  app="${info%%,*}"; app="${app// /}"
  title="${info#*,}"; title="${title# }"
else
  app=$(osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true' 2>/dev/null || echo "Unknown")
fi

ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# --- 2. 先写库拿 id（截图文件名用 id 命名，便于 analyze.py 回填） -----------
shot_taken=0
if [[ -z "$NO_SHOT" ]]; then shot_taken=1; fi
sample_id=$($PY "$SCRIPT_DIR/db.py" _insert "$ts" "$app" "$title" "$shot_taken" 2>/dev/null) || sample_id=""

if [[ -z "$sample_id" ]]; then
  echo "capture: 写数据库失败，跳过本次" >&2
  exit 1
fi

# --- 3. 截图（仅当启用）—— 多显示器：每块屏各截一张 ----------------------
# 文件名：<id>.d1.png, <id>.d2.png ...；analyze.py 按 <id>.dN 匹配回填。
# 理由：screencapture 默认只截主屏，外接屏会漏；逐屏截最准，且每张独立缩送 5v 清晰度好。
shot_ok=0
if [[ -n "$shot_taken" ]] && (( shot_taken )); then
  disp_count=0
  # system_profiler 数有几个非镜像 Resolution，即有几块屏
  disp_count=$(system_profiler SPDisplaysDataType 2>/dev/null | grep -c "Mirror: Off")
  (( disp_count < 1 )) && disp_count=1   # 兜底：至少截 1 块
  for d in $(seq 1 "$disp_count"); do
    shot_path="$SHOTS_DIR/$sample_id.d${d}.png"
    if screencapture -x -D "$d" "$shot_path" >/dev/null 2>&1 && [[ -s "$shot_path" ]]; then
      shot_ok=1
    else
      rm -f "$shot_path"   # 该屏失败（如屏号超界）就跳过，不影响其他屏
    fi
  done
  if (( shot_ok == 0 )); then
    # 全部屏都失败：标为未截图，避免 analyze.py 干等
    $PY "$SCRIPT_DIR/db.py" _set_no_shot "$sample_id" 2>/dev/null || true
  fi
fi

echo "captured: id=$sample_id | $ts | $app | $title"
if (( shot_ok )); then
  n=$(ls "$SHOTS_DIR"/"$sample_id".d*.png 2>/dev/null | wc -l | tr -d ' ')
  echo "  └ 已暂存 ${n} 块屏的截图（待 AI 分析后删除）"
fi
