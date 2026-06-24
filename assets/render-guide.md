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

- **`{{ITEMS_TITLE}}`** items 区的标题（如"今日完成"/"本周进展"/"主要成果"）。条目：
  ```html
  <li><span class="badge done">完成</span>事项文本</li>
  <li><span class="badge doing">进行中</span>事项文本</li>
  <li><span class="badge plan">计划</span>事项文本</li>
  ```
- **`{{DWELL_TITLE}}`** dwell 区标题（如"工作分布"/"投入占比"）。每条：
  ```html
  <div class="dwell-row"><div class="app">Code</div><div class="bar"><i style="width:100%"></i></div><div class="dur">1h05m</div></div>
  ```
  `width` = 该 App 时长 / 最大时长 × 100（取整）。时长来自 `aggregate.py --json` 的 `summary.dwell`。
- **`{{TIMELINE_TITLE}}`** timeline 区标题（如"时间线"）。每条 `.ev`：
  ```html
  <div class="ev">
    <span class="t">09:00</span><span class="app">Code</span>
    <div class="what">main.ts — MyEditor</div>
    <div class="desc">AI 截图描述</div>
  </div>
  ```

## 各报告类型用哪些 SLOT

| 类型 | overview | items | dwell | timeline |
|------|----------|-------|-------|----------|
| daily  | 删 | 今日完成/进行中/明日计划 | 可选 | 用 |
| weekly | 删 | 本周进展/产出/风险/下周计划 | 工作分布 | 可选 |
| monthly| 本月概览 | 成果/改进/下月计划 | 投入占比 | 删 |

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
