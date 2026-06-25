#!/usr/bin/env bash
# idle.sh — 检测当前是否空闲（鼠标键盘长时间无操作 / 屏保运行）
#
# 输出两行（供 capture.sh 解析）：
#   第1行：空闲秒数（整数）
#   第2行：screensaver=1（屏保运行）或 screensaver=0
#
# 用法：
#   ./idle.sh                 # 默认阈值 10 分钟（≥则视为空闲）
#   ./idle.sh 5               # 自定义阈值（分钟）
#   返回码：0=活跃，1=空闲（≥阈值或屏保）
#
# 环境变量:
#   AI_DAILY_IDLE_MINS  空闲阈值（分钟），默认 10；命令行参数优先
set -euo pipefail

THRESHOLD_M="${1:-${AI_DAILY_IDLE_MINS:-10}}"

# HIDIdleTime：自上次鼠标/键盘输入以来的纳秒数（系统级）
idle_ns=$(ioreg -c IOHIDSystem -l 2>/dev/null | perl -ne 'print "$1\n" if /"HIDIdleTime" = (\d+)/' | head -1)
idle_ns="${idle_ns:-0}"
idle_s=$(( idle_ns / 1000000000 ))

# 屏保是否运行
if pgrep -x "ScreenSaverEngine" >/dev/null 2>&1; then
  ss=1
else
  ss=0
fi

echo "$idle_s"
echo "screensaver=$ss"

# 判定：屏保运行 或 空闲≥阈值 → 空闲（返回1）
thresh_s=$(( THRESHOLD_M * 60 ))
if (( ss == 1 )) || (( idle_s >= thresh_s )); then
  exit 1
fi
exit 0
