"""classify.py — 基于 app 名把活动归类到 5 个分类。

借鉴 Dayflow 的分类思想（Work/Communication/Distraction/Personal/Idle），
用 app 名做规则映射。分类是周报"专注模式"统计的基础。

为什么需要分类：光知道"用了 Chrome 60 分钟"没意义——可能是查文档（work），
也可能刷微博（distraction）。分类让周报能说清"这周真正专注工作多久、分心多久"。

被 capture.sh（采时分类）和 aggregate.py（统计）复用。
"""
from __future__ import annotations

import re

# 分类常量
WORK = "work"
COMMUNICATION = "communication"
DISTRACTION = "distraction"
PERSONAL = "personal"
IDLE = "idle"

# 颜色（用于 HTML 报告，与 Dayflow 风格对齐）
CATEGORY_COLORS = {
    WORK: "#6A7EFF",          # 蓝紫 - 专注工作
    COMMUNICATION: "#FFAE8C", # 橙 - 沟通
    DISTRACTION: "#FF5950",   # 红 - 分心
    PERSONAL: "#ADE3E3",      # 青 - 个人事务
    IDLE: "#A0AEC0",          # 灰 - 空闲
}

CATEGORY_LABELS = {
    WORK: "工作",
    COMMUNICATION: "沟通",
    DISTRACTION: "分心",
    PERSONAL: "个人",
    IDLE: "空闲",
}

# --- 规则表：app 名（小写、包含匹配）→ 分类 ---
# 顺序敏感：先匹配先返回。distraction 要在 communication 前判断（如微博算分心）。
# 规则用"关键词包含"匹配，覆盖中英文 app 名。
_DISTRACTION_APPS = [
    "微博", "抖音", "tiktok", "快手", "bilibili", "哔哩哔哩", "b站",
    "youtube", "netflix", "spotify", "网易云音乐", "qq音乐",
    "x ", "twitter", "instagram", "facebook", "小红书", "知乎",
    "游戏", "steam", "epic games",
    "safari",  # safari 默认算分心（浏览），除非标题里是工作文档——后者由 title 细分覆盖
]

_COMMUNICATION_APPS = [
    "微信", "wechat", "企业微信", "wecom", "飞书", "lark", "feishu",
    "slack", "钉钉", "dingtalk", "telegram", "discord",
    "mail", "outlook", "spark", "airmail", "foxmail",
    "zoom", "腾讯会议", "teams", "webex", "google meet",
    "messages", "信息", "imessage", "qq",
]

_WORK_APPS = [
    "code", "vscode", "visual studio", "cursor", "sublime", "vim", "neovim",
    "intellij", "pycharm", "webstorm", "goland", "rustrover", "clion",
    "xcode", "android studio", "zcode",
    "iterm", "terminal", "warp", "kitty", "alacritty",
    "figma", "sketch", "adobe", "photoshop", "illustrator", "canva",
    "notion", "obsidian", "typora", "bear", "logseq",
    "tableau", "jupyter", "postman", "docker", "dataspell",
    "github", "gitlab", "sourcetree", "fork",
    "confluence", "jira", "linear",
]

_PERSONAL_APPS = [
    "支付宝", "alipay", "银行", "招商银行", "工行",
    "日历", "calendar", " reminders", "提醒",
    "淘宝", "京东", "美团", "大众点评", "携程",
    "keep", "健身",
    "照片", "photos",
]


def _match(app_lower: str, keywords: list[str]) -> bool:
    """app 名是否包含任一关键词。"""
    return any(k in app_lower for k in keywords)


def classify(app: str, title: str = "", status: str = "active") -> str:
    """返回 app/title 的分类。idle 状态直接返回 idle。

    优先级：idle > 标题里的工作信号 > distraction > communication > work > personal > 兜底 work。
    标题信号覆盖 app 分类：如 Safari 打开的是"API 文档"→work，打开的是"微博热搜"→distraction。
    """
    if status == IDLE or app in ("—", "Unknown", ""):
        return IDLE

    a = app.lower().strip()
    t = (title or "").lower()

    # 标题里的工作信号能"提升"分类：浏览器在看文档/代码/邮件算 work
    work_title_signals = ["文档", "docs", "documentation", "api", "stackoverflow", "github",
                          ".md", ".py", ".ts", ".js", "论文", "paper", "arxiv", "learnn",
                          "tutorial", "教程", "stack overflow"]
    if _match(a, ["safari", "chrome", "firefox", "edge", "arc", "brave"]):
        # 浏览器：先看标题
        if any(s in t for s in work_title_signals):
            return WORK
        if _match(t, _DISTRACTION_APPS) or any(s in t for s in ["热搜", "feed", "视频", "video", "直播"]):
            return DISTRACTION
        if _match(t, _COMMUNICATION_APPS):
            return COMMUNICATION
        return WORK  # 浏览器默认算 work（多数是在查资料），除非明确是分心内容

    # 非浏览器：按 app 名匹配
    if _match(a, _DISTRACTION_APPS):
        return DISTRACTION
    if _match(a, _COMMUNICATION_APPS):
        return COMMUNICATION
    if _match(a, _WORK_APPS):
        return WORK
    if _match(a, _PERSONAL_APPS):
        return PERSONAL
    # 兜底：无法识别的 app 默认算 work（多数桌面 app 是工作用的）
    return WORK


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == "_one":
        # CLI: classify.py _one <app> [title]  → 输出分类（供 capture.sh 调用）
        app = sys.argv[2] if len(sys.argv) > 2 else ""
        title = sys.argv[3] if len(sys.argv) > 3 else ""
        print(classify(app, title))
        raise SystemExit(0)

    # 自测：python3 classify.py
    cases = [
        ("Code", "main.ts", WORK),
        ("GoogleChrome", "Python 文档 - Google Chrome", WORK),
        ("GoogleChrome", "微博热搜 - Google Chrome", DISTRACTION),
        ("WeChat", "", COMMUNICATION),
        ("企业微信", "#技术团队", COMMUNICATION),
        ("Safari", "抖音", DISTRACTION),
        ("Spotify", "", DISTRACTION),
        ("支付宝", "", PERSONAL),
        ("Obsidian", "笔记", WORK),
        ("—", "", IDLE),
    ]
    ok = 0
    for app, title, expect in cases:
        got = classify(app, title)
        mark = "✓" if got == expect else "✗"
        if got == expect:
            ok += 1
        print(f"  {mark} {app:<14} | {title:<30} → {got} (期望 {expect})")
    print(f"\n{ok}/{len(cases)} 通过")
