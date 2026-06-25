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
- **隐私设计**：
  - 轨迹数据（应用/窗口/描述）仅存**本地 SQLite**，不主动上传。
  - **截图分析后本地即删**——AI 看图生成文字描述后立即删除原图，数据库只存文字描述。
  - 但截图分析本身会经过外部 AI 服务，**请务必阅读下方的「隐私风险」章节**。
- **HTML 报告**：白底绿色调卡片式布局，含停留时长进度条、任务清单、时间线，可打印为 PDF。

## ⚠️ 隐私风险（使用前必读）

本技能要截屏、要读取窗口标题、要把图发给 AI 看——这些都涉及你的隐私。**请在了解以下风险后再决定是否使用：**

### 风险 1：截图会捕捉屏幕上的全部可见内容

截图不是"只截当前应用"，而是**整块屏幕的像素**。这意味着截图里可能包含：

- 聊天记录、邮件、文档内容（即使你在看的是别的窗口）
- 浏览器里的页面、密码管理器之外的输入框内容
- 通知、系统弹窗、桌面上的任何东西
- 其他显示器上的所有内容（多屏模式每块屏都截）

**多显示器尤其要注意**：本技能会截取每一块屏。外接屏上如果有不该被记录的内容（如私聊、财务页面），也会被采到。

### 风险 2：截图分析时会经过外部 AI 服务

"截图分析后即删"指的是**本地原图删除**。但分析过程本身——把缩小后的截图传给视觉模型（如 5v）识别——意味着**那张缩小图经过了外部服务器**：

- 你无法控制外部服务是否缓存、保留、日志记录该图。
- 即便本地立即删除，云端可能留有传输/处理记录。
- 使用的视觉模型如果是第三方托管，适用该第三方的隐私政策。

**这是本技能最大的隐私权衡点。** 如果你的屏幕常含敏感信息（公司机密、个人隐私、医疗财务），请慎重开启截图。

### 风险 3：窗口标题本身泄露信息

窗口标题常包含**文件名、项目名、对话主题、邮件标题、网页标题**。这些文本会直接、持久地存进本地数据库（不删除），本身就是一份你的活动记录。例如标题 `保密项目X-架构设计.docx` 就暴露了你在做某个保密项目。

### 风险 4：本地数据未加密

`~/.ai-daily/ai_daily.db` 是**明文 SQLite**，没有加密。本机任何有读权限的程序/用户都能直接打开看到全部轨迹和描述。

### 风险 5：后台持续被动记录

`watch.sh` 一旦运行，**每 5 分钟自动采一次，不论你在做什么**。这意味着可能录到你不希望被记录的时段（如午休看视频、处理私事）。记录是"被动"的，不会主动询问你"现在能截吗"。

### 缓解措施

| 措施 | 怎么做 | 降低哪个风险 |
|------|--------|-------------|
| **隐私模式（不截图）** | `AI_DAILY_NO_SHOT=1 bash watch.sh` | 1、2（完全不截图，只记应用/窗口，仍能生成日报） |
| **仅在特定时段记录** | 手动启动/停止 watch，不要全天挂着 | 5 |
| **敏感时刻手动暂停** | `pkill -f watch.sh` 临时停；之后再启 | 1、5 |
| **缩短采样间隔的副作用** | 间隔越短捕捉越细，但漏记也越少——按需权衡 `watch.sh <分钟>` | — |
| **定期清理数据** | 见 SKILL.md「数据与隐私管理」 | 3、4 |
| **别在敏感屏/项目上用截图模式** | 或给数据目录加密（需自行配置 FileVault/加密卷） | 1、4 |

**最稳妥的做法**：如果在意风险 2（图经过外部服务），就用隐私模式（`AI_DAILY_NO_SHOT=1`），彻底不截图，只靠应用名+窗口标题生成日报。这样数据全程不出本机。

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
