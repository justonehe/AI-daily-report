#!/usr/bin/env bash
# watch.sh — 前台循环采样器
#
# 每隔固定间隔调用一次 capture.sh，把一天的工作轨迹持续写入本地 SQLite。
# 截图暂存在 screenshots/ 下，等要日报时由 analyze.py 统一交给 AI 分析并删除。
# 设计为"前台常驻": Ctrl-C 停止。真正想后台常驻请用 launchd（见 SKILL.md）。
#
# 用法:
#   ./watch.sh                 # 默认每 5 分钟一次
#   ./watch.sh 10              # 每 10 分钟一次
#   AI_DAILY_NO_SHOT=1 ./watch.sh   # 只记 App/窗口，不截图（截图分析也跳过）
#
# 环境变量（透传给 capture.sh）:
#   AI_DAILY_DIR     数据目录
#   AI_DAILY_NO_SHOT 跳过截图
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAPTURE="$SCRIPT_DIR/capture.sh"
INTERVAL_M="${1:-5}"

if ! [[ "$INTERVAL_M" =~ ^[0-9]+$ ]] || (( INTERVAL_M < 1 )); then
  echo "watch.sh: 间隔必须是正整数（分钟），得到: '$INTERVAL_M'" >&2
  exit 2
fi

interval_s=$((INTERVAL_M * 60))
echo "AI日报助手 — 开始记录工作轨迹（每 ${INTERVAL_M} 分钟一次，Ctrl-C 停止）"

# trap INT/TERM，给个友好退出而不是堆栈
stop=0
trap 'stop=1; echo; echo "停止记录，已保存到 SQLite"' INT TERM

# 首次立即采一次，之后按间隔循环
bash "$CAPTURE" || true
while (( stop == 0 )); do
  # 用可中断的等待：把长间隔拆成 1 秒的轮询，收到信号能及时退出
  waited=0
  while (( stop == 0 && waited < interval_s )); do
    sleep 1 || exit 0
    waited=$((waited + 1))
  done
  (( stop == 0 )) && bash "$CAPTURE" || true
done
