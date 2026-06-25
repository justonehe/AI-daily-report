# HTML 报告渲染指南

把 `aggregate.py` 的素材渲染成 HTML 报告的规则。读 `report-template.html` 作为骨架，按 SLOT 规则填充。

## SLOT 注入规则

模板里有 4 个 SLOT 块，每块形如：

```html
<!-- SLOT: xxx -->
...占位 section...
<!-- /SLOT: xxx -->
```

处理每个 SLOT：

- **要用**：把【从 `<!-- SLOT: xxx` 到 `<!-- /SLOT: xxx -->` 的整块】（含两个标记）替换成真实 section HTML。
- **不用**：把【整块】（含标记）删除，留空字符串。**不要留空 section**。

## 头部占位符（必填）

```html
{{TITLE}}      报告标题，如 "日报 · 2026-06-24"
{{SUBTITLE}}   副标题，如 "今日工作回顾 — AI日报助手"
{{META1_VAL}} {{META1_LABEL}}   一个统计项的值+标签（如 9 / 采样数）
{{META2_VAL}} {{META2_LABEL}}   第二项（如 5 / 带截图描述）
{{META3_VAL}} {{META3_LABEL}}   第三项（如 2h00m / 记录时长）
```

## 各 SLOT 内容

### activity-grid（日报顶部热力图）

24 格，每格代表一小时。数据来自 `aggregate --json` 的 `activity_grid`（长度 24 的数组，值=该小时活跃样本数）。
```html
<div class="grid">
  <div class="col"><div class="cell l3"></div><div class="hr">9</div></div>
  ...
</div>
```
level 映射（按样本数）：0→`l0`(无 class, 灰)，1→`l1`，2-3→`l2`，4-5→`l3`，≥6→`l4`。只显示有活动的时段范围（如 8-20 点），两端全 0 的可裁掉。标题用 `<section><h2>今日活动</h2><div class="card">...</div></section>`。

### standup（日报三栏）

借鉴 Dayflow 的 standup 视图，三栏并排：
```html
<div class="three-col">
  <div class="panel hi"><h3>★ 昨日亮点</h3><ul><li>事项1</li>...</ul></div>
  <div class="panel pri"><h3>◆ 今日重点</h3><ul><li>事项1</li>...</ul></div>
  <div class="panel blk"><h3>⚑ 阻塞项</h3><ul><li>事项1</li>...</ul></div>
</div>
```
- **昨日亮点**：从昨天（-1天）的 samples 里挑完成的代表性事项。用 `aggregate --day <昨天>` 取数据。
- **今日重点**：从今天轨迹归纳出的核心工作（≤5 条）。
- **阻塞项**：轨迹里体现"等待/卡住"的（如长时间在通讯软件、重复查看同一页面），或 AI 推断的卡点。

### items / dwell / timeline（原有，不变）

- **`{{ITEMS_TITLE}}`** items 区标题。条目：
  ```html
  <li><span class="badge done">完成</span><span class="txt">事项文本</span></li>
  ```
- **`{{DWELL_TITLE}}`** dwell 区标题。每条：
  ```html
  <div class="dwell-row"><div class="app">Code</div><div class="bar"><i style="width:100%"></i></div><div class="dur">1h05m</div></div>
  ```
  `width` = 该 App 时长 / 最大时长 × 100。时长来自 `summary.dwell`。
- **`{{TIMELINE_TITLE}}`** timeline 区标题。每条 `.ev`（idle 段加 `class="ev idle"`）：
  ```html
  <div class="ev">
    <span class="t">09:00</span><span class="app">Code</span>
    <div class="what">main.ts — MyEditor</div>
    <div class="desc">AI 截图描述</div>
  </div>
  ```

### focus（周报专注模式）

数据来自 `aggregate --json` 的 `app_focus`（按 App 的连续专注块统计）。每条：
```html
<div class="focus-row">
  <div class="app">Code</div>
  <div class="blk">3块</div>
  <div class="bar"><i style="width:100%"></i></div>
  <div class="dur">1h20m</div>
</div>
```
`minutes` 转成时长显示，`width` = 该 App 专注总时长 / 最大值 × 100。

## 各报告类型用哪些 SLOT

| 类型 | activity-grid | standup | overview | items | focus | dwell | timeline |
|------|---------------|---------|----------|-------|-------|-------|----------|
| daily  | ✅ 用 | ✅ 用 | 删 | 可选(细化) | 删 | 可选 | 用 |
| weekly | 删 | 删 | 删 | 本周进展 | ✅ 用 | 工作分布 | 可选 |
| monthly| 删 | 删 | 本月概览 | 成果/改进 | 可选 | 投入占比 | 删 |

## 推理规则（AI 引擎职责，不是搬运素材）

1. **合并相邻相关样本**：连续在 IDE ↔ 浏览器文档间切换 = 同一件事的不同动作，合并成一条时间线事件或多条 items 共指。
2. **用窗口标题推断具体内容**：文件名/分支名/issue 号能写具体就写具体。
3. **"完成"要有结果，"进行中"说清卡点**。
4. 周报按项目/主题归类，月报按阶段成果合并——粒度越粗越合并同类项。

## 收尾（必须）

填充完后扫描最终 HTML：

1. 不得残留任何 `{{...}}` 占位符（用正则 `\{\{[A-Z_]+\}\}` 查，注释里的说明文字不算）。
2. 不得残留 `<!-- SLOT` / `<!-- /SLOT` 标记。
3. 删掉模板里那行"渲染规则见..."的开发注释。
4. 空的 `<section>` 要整个删掉。

完整填充范例见 `example-daily.html`。
