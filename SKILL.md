---
name: ai-daily-report
description: 由 AI 驱动的"AI日报助手"——帮职场人自动记录工作轨迹并一键生成日报/周报/月报（HTML）。当用户想生成今日日报、本周周报、本月月报，或提到"今天做了什么""写日报""工作总结""忘记今天干了啥""自动记录工作"等场景时使用此 skill。通过定时截图 + 前台应用/窗口标题记录工作轨迹，AI 分析截图后**立即删除图片只留文字描述**，再把轨迹推理成标准流畅的日报。所有数据仅存本地 SQLite，绝不上传。
---

# AI日报助手

AI 驱动的工作日报工具。两条核心承诺贯穿始终：

- **自动记录工作轨迹**：定时（默认每 5 分钟）采集一次"当前前台应用 + 窗口标题 + 屏幕截图"，告别"想不起今天做了什么"。
- **智能生成日报**：把一段时间的轨迹聚合成"素材"（停留时长 + 时间线 + 截图描述），由 AI 套 HTML 模板推理成流畅报告。

## 🔒 隐私承诺（必须遵守）

1. **数据仅存本地**：所有记录、报告存在本地 SQLite（`~/.ai-daily/ai_daily.db`），**绝不上传**任何外部服务。
2. **截图分析后即删**：截图是"临时文件"，AI 看图生成一句文字描述后**立即 `rm` 删除原图**。数据库里只存文字描述，屏幕像素内容绝不持久化。

这两条是本工具的底线。任何工作流都不得把截图内容发给外部，也不得绕过删除步骤。

## 工作原理

```
watch.sh ─每5分→ capture.sh ─写→ SQLite(samples) + 暂存截图 screenshots/<id>.png
                                      │
              要日报时(AI在场):         │
              1. analyze.py --list ────┘  列出待分析截图
              2. AI 逐张读图 → analyze.py _set <id> "描述"  (写描述 + 删图)
              3. aggregate.py  聚合 samples → 素材(停留时长+时间线)
              4. AI 套 assets/report-template.html → reports/<类型>-<日期>.html
```

**职责分离**：
- `scripts/`（记录器）只忠实记录原始信号、管存储和删图，不做语义加工。
- **AI 引擎（即你，加载本 skill 的 Agent）**负责"看图说话"和"把轨迹推理成工作事项"——脚本没有视觉和语义能力。

## 数据位置

默认 `~/.ai-daily/`（`AI_DAILY_DIR` 可改）：

```
~/.ai-daily/
├── ai_daily.db             # SQLite：samples + reports 两表（唯一持久化数据源）
├── screenshots/            # 临时！待分析截图 <id>.png，analyze 后即删
└── reports/                # 生成的 HTML 报告
```

数据库两表：`samples(ts, app, title, description, shot_taken, analyzed)`、`reports(kind, period, path, created_at)`。**description 是截图的文字描述，不含图片**。

## 首次使用：权限（macOS）

capture.sh 需要"自动化"和"屏幕录制"权限。首次运行时：

1. macOS 弹"自动化"授权框（控制 System Events）——点允许。
2. 若开启截图，在 `系统设置 → 隐私与安全性 → 屏幕录制` 给终端/IDE 授权。

不想截图 / 拿不到屏幕录制权限 → 隐私模式（只记应用/窗口）：

```bash
export AI_DAILY_NO_SHOT=1   # 当前 shell 生效；或每次命令前加
```

隐私模式下"今天做了什么"依然可用（应用 + 窗口标题已够推理），只是没有截图描述佐证，analyze 步骤会自动跳过。

## 命令清单

`$SK` = skill 目录（`~/.agents/skills/ai-daily-report`）。

| 操作 | 命令 | 说明 |
|------|------|------|
| 采一次样本 | `bash $SK/scripts/capture.sh` | 写库 + 暂存截图 |
| 持续记录 | `bash $SK/scripts/watch.sh` | 前台常驻，Ctrl-C 停 |
| 指定间隔 | `bash $SK/scripts/watch.sh 10` | 每 10 分钟 |
| 隐私模式 | `AI_DAILY_NO_SHOT=1 bash $SK/scripts/watch.sh` | 不截图 |
| 检查数据库 | `python3 $SK/scripts/db.py` | 初始化/看条数 |
| 列待分析截图 | `python3 $SK/scripts/analyze.py --list` | 生成报告前先跑 |
| 存描述+删图 | `python3 $SK/scripts/analyze.py _set <id> "描述"` | AI 读图后逐张调 |
| 放弃分析清空 | `python3 $SK/scripts/analyze.py --purge` | 直接删所有暂存图 |
| 生成今日素材 | `python3 $SK/scripts/aggregate.py` | 默认今天，输出 Markdown |
| 某天/周/月 | `python3 $SK/scripts/aggregate.py --day/--week/--month` | |
| 素材 JSON | `python3 $SK/scripts/aggregate.py --json` | 程序化消费 |

## 工作流 A：开始记录一天

用户说"开始记录我的一天""帮我记录工作""开始工作轨迹"时：

1. 后台运行 `bash $SK/scripts/watch.sh`（用 `run_in_background`，不阻塞会话）。隐私模式加 `AI_DAILY_NO_SHOT=1`。
2. 告诉用户：已在后台记录，每 5 分钟一次；下班或想要日报时说一声。
3. 不要让记录阻塞你继续响应其他请求。

## 工作流 B：生成日报（核心场景）⭐

用户说"帮我写今天的日报""今天做了什么""生成日报/周报/月报"时，**严格按 4 步**：

**步骤 1 — 判断范围**：日报默认/`--day`；周报 `--week`；月报 `--month`。用户给了具体日期就用那个。

**步骤 2 — 分析截图（隐私关键步，必须做）**：
```bash
python3 $SK/scripts/analyze.py --list
```
多显示器：一个样本可能有多张图（`<id>.d1.png`、`<id>.d2.png`...，每块屏一张）。对列出的**每个样本的所有截图**，合并出一句"在做什么"的描述。**优先用 `mcp__4_5v_mcp__analyze_image` 工具（5v 视觉模型）**，它对中文文字识别比模型自身视觉更准：

1. **缩小截图**（关键！真实截图约 2-3MB，直接 Read 会内联、拿不到 CDN URL）。对每张 `<id>.dN.png` 缩到宽 1100px、JPEG：
   ```bash
   python3 -c "from PIL import Image; im=Image.open('$HOME/.ai-daily/screenshots/<id>.d<N>.png').convert('RGB'); w,h=im.size; im.resize((1100,int(h*1100/w))).save('/tmp/<id>.d<N>.jpg','JPEG',quality=85)"
   ```
2. 用 `Read` 工具读每张缩小后的 `/tmp/<id>.d<N>.jpg`——小图会触发上传，返回**带签名的 CDN URL**。
3. 把各 CDN URL 传给 `mcp__4_5v_mcp__analyze_image`，prompt 用："这张截图显示的是什么应用/界面？屏幕上的主要文字内容是什么？用一句话概括用户在做什么。"多屏样本综合各屏内容，凝练成**一句**描述。
4. 拿到 5v 返回的描述，结合已知的 app/title 上下文，凝练成一句中文描述（如"在浏览器里查登录鉴权的文档，对比 JWT 与 session 方案"）。
5. 立即执行 `python3 $SK/scripts/analyze.py _set <id> "描述"` ——这会**把描述写库并删除该样本所有屏的截图**。最后 `rm /tmp/<id>.d*.jpg` 清掉缩略图。

> **5v 工具的坑（实测）**：① 只接受**远程 URL**，传本地路径会报 `1210 图片格式/解析错误`；所以必须先 Read 上传拿 CDN URL。② 大图（>200KB）Read 会内联不返回 URL，**必须先缩小**。③ 低分辨率小图上的中文可能识别成方块，宽 1100px 下中文识别准确。
> **兜底**：若 5v 工具不可用，退回到用你自己的视觉能力（Read 图片后直接描述）。若用户不想让你看图，或图太多，跑 `analyze.py --purge` 直接清空暂存图（不生成描述），聚合仍可用 app/title。

- 全部处理完，`--list` 应显示"没有待分析的截图"。**确认没有截图残留**。

**步骤 3 — 聚合素材**：
```bash
python3 $SK/scripts/aggregate.py <范围参数>
```
拿到 Markdown：停留时长 Top + 时间线（每条带 AI 截图描述）。

**步骤 4 — AI 推理生成 HTML 报告**（你的核心职责）：
- 读 `assets/report-template.html`，按日/周/月选区块（见模板内注释）。
- **必须推理**，不是搬运素材：
  - 相邻相关样本（如连续在 IDE ↔ 浏览器文档间切换）合并成"同一件事"。
  - 用窗口标题里的文件名/分支名/issue 号推断具体内容。
  - "完成"要有结果，"进行中"说清卡点。
  - 周报按项目/主题归类，月报按阶段成果合并——粒度越粗越合并。
- `{{...}}` 占位符全替换；停留时长条的 `width` = 该 App 时长/最大时长×100%。
- 不需要的 `<section>` 整段删掉，不要留空壳。
- 保存到 `~/.ai-daily/reports/<类型>-<日期>.html`（如 `daily-2026-06-24.html`），并写一条 reports 记录：`python3 $SK/scripts/db.py` 暂未暴露写 reports 的 CLI，直接用 `python3 -c "import sys;sys.path.insert(0,'$SK/scripts');import db;db.insert_report('daily','2026-06-24','<绝对路径>')"`。
- 把 HTML 路径告诉用户（可用浏览器打开 / 打印为 PDF）。

**素材为空时**（aggregate 提示"没有采集到样本"）：直接告诉用户原因（没运行 watch.sh / 日期错 / `AI_DAILY_DIR` 指错），**不要编造日报**。

## 工作流 C：数据与隐私管理

- **看库里有什么**：`python3 $SK/scripts/db.py`。
- **清空所有暂存截图**：`python3 $SK/scripts/analyze.py --purge`（不生成描述）。
- **彻底删某天数据**：从 SQLite 删 samples（需 SQL），并确认 screenshots/ 无残留。删除前和用户确认。
- **全量备份/导出**：打包 `~/.ai-daily/`（含 db + reports；截图通常已被分析删除）。

## 常见问题排查

- **应用名 `Unknown` / 标题为空**：未授权"自动化"。`系统设置 → 隐私与安全性 → 自动化` 允许终端控制 System Events。
- **截图失败**：未授权"屏幕录制"，或屏幕锁定。授权或用 `AI_DAILY_NO_SHOT=1`。
- **aggregate 提示没样本**：watch.sh 没在该时段运行 / 日期错 / `AI_DAILY_DIR` 指错。先 `python3 db.py` 看条数。
- **analyze --list 一直有残留**：说明你漏了某些 `_set`。报告生成前必须让列表清空（或显式 `--purge`）。

## 附录：launchd 后台常驻（可选，高级）

仅当用户明确要"开机自动记录 / 关终端也跑"时提供。存为 `~/Library/LaunchAgents/com.ai.daily.plist` 后 `launchctl load`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.ai.daily</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>__SKILL_DIR__/scripts/capture.sh</string>
  </array>
  <key>StartInterval</key><integer>300</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardErrorPath</key><string>/tmp/ai-daily-capture.err.log</string>
</dict></plist>
```

注意 launchd 进程同样需要"自动化/屏幕录制"权限，且授权对象是 launchd 宿主，首次配置较麻烦。**默认推荐前台 watch.sh**。
