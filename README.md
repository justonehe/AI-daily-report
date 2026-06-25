# AI 日报助手（AI Daily Report）

> 一个**给 AI Agent 用的 Skill**：让 agent 能自动记录用户的工作轨迹，并一键生成日报 / 周报 / 月报（HTML）。
>
> **这不是独立 App 或 CLI**——它是一份"技能说明书 + 脚本"，由支持 skill 的 AI Agent（如 ZCode、Claude Code、Codex 等）加载后执行。Agent 负责编排和看图推理，脚本负责采集、存储、聚合。

---

## 🤖 给 Agent 的安装指南（Agent 可自助完成）

如果用户把本仓库链接粘给你（Agent），请按以下步骤安装。**每步都给了可执行命令和验证方式**，照着做即可。

### 第 0 步：确认你是能安装 skill 的 Agent

本 skill 适用于支持 `SKILL.md` 自动发现的 Agent（如 ZCode、Claude Code 等）。判断标志：你的工作目录或 `~/.agents/skills/` 下已有其他 `*/SKILL.md` 形式的技能。

### 第 1 步：克隆到 skills 目录

skills 的标准位置（按你 Agent 的规范二选一）：

- **用户级**（推荐，全局生效）：`~/.agents/skills/`
- **项目级**（仅当前仓库）：`<repo>/.agents/skills/`

```bash
# 用户级安装（默认推荐）
git clone https://github.com/justonehe/AI-daily-report.git ~/.agents/skills/ai-daily-report
```

> ⚠️ 目录名必须是 `ai-daily-report`（与 SKILL.md 的 `name` 字段一致），否则 skill 无法被识别。

### 第 2 步：给脚本加可执行权限

```bash
chmod +x ~/.agents/skills/ai-daily-report/scripts/*.sh ~/.agents/skills/ai-daily-report/scripts/*.py
```

### 第 3 步：检查依赖

```bash
# macOS 自带的（一般都有）
command -v screencapture osascript system_profiler python3
# Python 版本需 3.8+
python3 --version
```

验证：以上命令都有输出、python3 ≥ 3.8。缺 screencapture/osascript 说明不是 macOS，本 skill 当前仅支持 macOS。

### 第 4 步：验证安装成功

```bash
# 应输出 "数据库就绪：..." 且 samples/reports 计数
python3 ~/.agents/skills/ai-daily-report/scripts/db.py
```

看到 `数据库就绪：/Users/<你>/.ai-daily/ai_daily.db` 即安装成功。

### 第 5 步：读主文档掌握用法

```bash
cat ~/.agents/skills/ai-daily-report/SKILL.md
```

**SKILL.md 是你的操作手册**——它定义了 3 个工作流（开始记录 / 生成日报 / 数据管理）和截图分析的完整流程。安装后请读一遍。

### 安装完成后告诉用户

> ✅ 已安装「AI日报助手」技能。
> - 首次使用需授权：系统设置 → 隐私与安全性 → 给终端「自动化」和「屏幕录制」权限。
> - 想记录工作时说"开始记录"，想生成日报时说"写今天的日报"。
> - 隐私说明：数据只存本地（`~/.ai-daily/`），截图分析后即删。

---

## 它做什么

通过定时截图 + 前台应用/窗口标题记录工作轨迹，AI 分析截图后**立即删除图片只留文字描述**，再把轨迹推理成标准流畅的日报。

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

## 核心特性

- **自动记录**：定时（默认每 5 分钟）采集前台应用 + 窗口标题 + 屏幕截图。支持**多显示器**（每块屏各截一张）。
- **智能生成**：AI 把轨迹聚合成素材（停留时长 + 时间线 + 截图描述），推理成流畅报告。
- **隐私优先**：
  - 所有数据仅存**本地 SQLite**，绝不上传。
  - **截图分析后即删**——AI 看图生成文字描述后立即删除原图，数据库只存文字描述，屏幕像素绝不持久化。
- **HTML 报告**：白底绿色调卡片式布局，含停留时长进度条、任务清单、时间线，可打印为 PDF。

## 文件结构

```
ai-daily-report/
├── SKILL.md                      # 触发条件 + 3 个工作流编排（Agent 的主文档）
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
- Python 3.8+（仅用标准库）
- 截图分析需 Agent 的视觉能力（如 5v 视觉模型 MCP 工具，或 Agent 自身多模态能力）

## 权限

首次使用需在「系统设置 → 隐私与安全性」授权：

- **自动化**：允许终端控制 System Events（取应用名 + 窗口标题）
- **屏幕录制**：允许终端截图

不想截图可用隐私模式：`AI_DAILY_NO_SHOT=1`（只记应用/窗口，仍可生成日报）

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
