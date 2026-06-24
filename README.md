# AI 日报助手（AI Daily Report）

由 AI 驱动的工作日报工具：自动记录工作轨迹，一键生成日报 / 周报 / 月报（HTML）。

## 核心特性

- **自动记录**：定时（默认每 5 分钟）采集前台应用 + 窗口标题 + 屏幕截图，告别"想不起今天做了什么"。支持**多显示器**（每块屏各截一张）。
- **智能生成**：AI 把轨迹聚合成素材（停留时长 + 时间线 + 截图描述），推理成流畅报告。
- **隐私优先**：
  - 所有数据仅存**本地 SQLite**，绝不上传。
  - **截图分析后即删**——AI 看图生成文字描述后立即删除原图，数据库只存文字描述，屏幕像素绝不持久化。
- **HTML 报告**：白底绿色调卡片式布局，含停留时长进度条、任务清单、时间线，可打印为 PDF。

## 工作流程

```
watch.sh ─每5分→ capture.sh ─写→ SQLite + 暂存截图(多屏各一张)
                                      │
              要日报时(AI在场):         │
              1. analyze.py --list ────┘  列出待分析截图
              2. AI 逐张读图(经 5v 视觉模型) → analyze.py _set <id> "描述"  (写描述 + 删图)
              3. aggregate.py  聚合 → 素材(停留时长+时间线)
              4. AI 套 report-template.html → reports/*.html
```

详细用法见 [`SKILL.md`](./SKILL.md)。

## 文件结构

```
ai-daily-report/
├── SKILL.md                      # 触发条件 + 3 个工作流编排（主文档）
├── scripts/
│   ├── capture.sh                # 单次采样：应用/窗口 + 多屏截图 → SQLite
│   ├── watch.sh                  # 前台循环采样器（Ctrl-C 停）
│   ├── db.py                     # SQLite 存储层（samples + reports 两表）
│   ├── analyze.py                # 截图分析协调器（登记/回填描述/删图）
│   └── aggregate.py              # 按日/周/月聚合 → 停留时长 + 时间线
└── assets/
    ├── report-template.html      # HTML 报告骨架（SLOT 注入）
    ├── example-daily.html        # 填充范例
    └── render-guide.md           # 渲染规则
```

## 环境要求

- macOS（用 `screencapture`、`osascript`、`system_profiler`）
- Python 3.8+（标准库即可，`aggregate.py` 用 stdlib）
- `jq`（capture.sh 写 JSON 时用；现已改用 Python，可选）
- 截图分析需 AI 引擎的视觉能力（如 5v 视觉模型 MCP 工具）

## 权限

首次使用需在「系统设置 → 隐私与安全性」授权：

- **自动化**：允许终端控制 System Events（取应用名 + 窗口标题）
- **屏幕录制**：允许终端截图

不想截图可用隐私模式：`AI_DAILY_NO_SHOT=1`

## 数据位置

默认 `~/.ai-daily/`（`AI_DAILY_DIR` 可改）：

```
~/.ai-daily/
├── ai_daily.db          # SQLite（samples + reports）
├── screenshots/         # 临时！待分析截图，analyze 后即删
└── reports/             # 生成的 HTML 报告
```

## 许可证

MIT
