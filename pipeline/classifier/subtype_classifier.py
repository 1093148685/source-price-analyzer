"""
Subtype Classifier — 产品子类识别。

基于产品大类的子分类规则，支持规则匹配 + AI 分类 + 降级兜底。
"""
from typing import Any
from ..schema import NormItem

# ── 子分类规则 ──
# 格式: { type_slug: [(subtype_slug, name, include_keywords, exclude_keywords, description), ...] }

SUBTYPE_RULES = {
    "chatgpt": [
        ("chatgpt-free", "ChatGPT Free / 免费号",
         ["free", "免费", "普号", "普通号", "白号", "free号"],
         ["plus", "pro", "team", "go订阅", "bug", "教程", "gemini", "notion", "日抛"],
         "免费/普号"),

        ("chatgpt-plus-account", "ChatGPT Plus 成品号",
         ["plus", "成品号", "账号"],
         ["充值", "官方", "正规", "pro", "team", "团队", "go ", "go订阅", "business", "bug", "教程", "gemini", "notion", "苹果", "日抛", "试用", "free", "免费", "普号", "白号", "空邮箱", "cursor", "codex", "接码"],
         "Plus 成品号/账号货源"),

        ("chatgpt-plus-official", "ChatGPT Plus 官方/正规充值",
         ["plus", "官方", "正规", "直充", "充值", "质保订阅", "卡密", "cdk", "ios", "内购"],
         ["成品", "日抛", "试用", "team", "团队", "go ", "go订阅", "business", "bug", "教程", "gemini", "key", "notion", "苹果", "apple", "礼品卡", "free", "免费", "普号"],
         "Plus 官方渠道/正规代充"),

        ("chatgpt-plus-temp", "ChatGPT Plus 日抛/试用",
         ["plus", "日抛", "试用"],
         ["官方充值", "正规充值", "team", "business", "go ", "go订阅", "bug", "教程", "gemini", "notion"],
         "Plus 日抛、试用"),

        ("chatgpt-pro-account", "ChatGPT Pro 成品号",
         ["pro", "成品", "账号"],
         ["prompt", "proxy", "proton", "plus", "team", "go ", "go订阅", "bug", "教程", "gemini", "notion"],
         "Pro 成品号/账号"),

        ("chatgpt-pro-official", "ChatGPT Pro 官方/代充",
         ["pro", "充值", "直充"],
         ["prompt", "proxy", "proton", "team", "go ", "go订阅", "bug", "教程", "gemini", "notion"],
         "Pro 会员充值/代充"),

        ("chatgpt-go", "ChatGPT Go",
         ["go", "go订阅", "8美元", "8 美元"],
         ["pro", "team", "bug", "教程", "gemini", "notion"],
         "ChatGPT Go 订阅"),

        ("chatgpt-team", "ChatGPT Team",
         ["team", "团队", "business"],
         ["go ", "go订阅", "bug", "教程", "gemini", "notion", "苹果"],
         "Team 团队订阅"),
    ],

    "codex-api": [
        ("codex-longterm", "Codex 长效接码",
         ["长效", "长期", "30天", "60天", "90天", "31-90", "28-30"],
         ["短效", "25min", "一次性", "试用"],
         "Codex 长效接码（30天+）"),
        ("codex-shortterm", "Codex 短效接码",
         ["短效", "一次性", "25min", "试用"],
         ["长效", "长期", "30天", "60天", "90天"],
         "Codex 短效/一次性接码"),
        ("codex-api-key", "API Key / Token",
         ["api", "key", "token", "额度"],
         ["中转", "反代", "接码"],
         "API Key、Token、额度"),
        ("codex-proxy", "API 中转/反代",
         ["中转", "反代"],
         ["接码", "账号", "成品"],
         "API 中转/反代"),
        ("codex-misc", "其他接码",
         ["接码"],
         [],
         "其他接码服务"),
    ],

    "microsoft-email": [
        ("hotmail-account", "Hotmail 邮箱",
         ["hotmail"],
         ["outlook", "空邮箱", "白号"],
         "Hotmail 邮箱账号"),
        ("outlook-account", "Outlook 邮箱",
         ["outlook"],
         ["hotmail", "空邮箱"],
         "Outlook 邮箱账号"),
        ("email-empty", "空邮箱/白号",
         ["空邮箱", "白号", "全新邮箱", "全新微软"],
         ["hotmail成品", "outlook成品", "gmail"],
         "未绑定的微软邮箱"),
        ("email-transfer", "邮箱换绑/交付",
         ["换绑", "邮箱交付", "转移", "绑邮箱", "绑定邮箱"],
         ["gmail", "谷歌邮箱"],
         "用于换绑的邮箱"),
    ],

    "claude": [
        ("claude-pro", "Claude Pro",
         ["pro"],
         ["prompt", "max", "5x", "20x", "team", "团队", "bug", "教程", "gemini", "grok", "notion", "兑换码", "额度", "刀"],
         "Claude Pro 会员"),
        ("claude-max", "Claude Max",
         ["max", "5x", "20x"],
         ["pro", "team", "bug", "教程", "gemini", "grok", "notion", "兑换码", "额度"],
         "Claude Max 会员"),
        ("claude-team", "Claude Team",
         ["team", "团队"],
         ["pro", "max", "bug", "教程", "gemini", "grok", "notion", "兑换码"],
         "Claude Team 会员"),
        ("claude-account", "Claude 成品号/普通号",
         ["成品", "账号", "普号", "普通"],
         ["pro", "max", "team", "bug", "教程", "gemini", "grok", "notion", "兑换码"],
         "Claude 账号"),
        ("claude-credits", "Claude 兑换码/额度",
         ["兑换码", "额度", "刀"],
         [],
         "Claude API 额度兑换码"),
    ],

    "grok": [
        ("grok-super", "Super Grok 会员",
         ["super", "会员"],
         ["api", "bug", "教程", "gemini", "claude", "notion"],
         "Super Grok 会员"),
        ("grok-account", "Grok 账号",
         ["账号", "成品", "普号"],
         ["super", "api", "bug", "教程", "gemini", "claude", "notion"],
         "Grok 账号"),
    ],

    "netflix": [
        ("netflix-premium", "Netflix 高级/4K",
         ["4k", "高级", "独享"],
         [],
         "Netflix 高级独享"),
        ("netflix-account", "Netflix 账号/车位",
         ["账号", "车位", "奈飞", "netflix"],
         [],
         "Netflix 账号或车位"),
    ],

    "cloud-drive": [
        ("quark-drive", "夸克网盘",
         ["夸克"],
         [],
         "夸克网盘"),
        ("baidu-drive", "百度网盘",
         ["百度网盘", "百度"],
         [],
         "百度网盘"),
        ("drive-tools", "网盘工具",
         ["助手", "工具"],
         [],
         "网盘工具"),
    ],

    "apple": [
        ("apple-id", "Apple ID 账号",
         ["apple id", "苹果id", "苹果账号"],
         ["游戏", "地铁", "吃鸡", "王者", "pubg", "原神", "教程"],
         "Apple ID 账号"),
        ("icloud", "iCloud / 苹果订阅",
         ["icloud", "订阅"],
         ["游戏", "地铁", "吃鸡", "王者", "pubg", "原神", "教程"],
         "iCloud 或苹果订阅"),
    ],

    "gemini": [
        ("gemini-pro", "Gemini Pro/Advanced",
         ["pro", "advanced", "2.5", "2.0"],
         ["api", "key", "token", "教程"],
         "Gemini Pro/Advanced 订阅"),
        ("gemini-account", "Gemini 账号",
         ["账号", "成品", "普号"],
         ["pro", "advanced", "api", "教程"],
         "Gemini 普通账号"),
        ("gemini-api", "Gemini API Key",
         ["api", "key", "token"],
         [],
         "Gemini API Key/Token"),
    ],

    "cursor": [
        ("cursor-pro", "Cursor Pro",
         ["pro", "订阅", "成品"],
         ["接码", "教程"],
         "Cursor Pro 订阅"),
        ("cursor-phone", "Cursor 接码",
         ["接码", "实卡", "验证"],
         [],
         "Cursor 手机验证/接码"),
    ],

    "dev-tools": [
        ("windsurf", "Windsurf",
         ["windsurf"],
         [],
         "Windsurf IDE"),
        ("devin", "Devin",
         ["devin"],
         [],
         "Devin AI"),
        ("copilot", "GitHub Copilot",
         ["copilot", "github"],
         [],
         "GitHub Copilot"),
        ("other-ide", "其他 AI IDE",
         ["replit", "bolt", "v0", "lovable", "cursory", "lovart", "tabnine", "cody"],
         [],
         "Replit/Bolt/v0 等"),
    ],

    "lessons": [
        ("ai-lesson", "AI 使用教程",
         ["ai", "gpt", "chatgpt", "claude", "codex", "gemini", "copilot", "ai教程"],
         [],
         "AI 工具使用教程"),
        ("dev-lesson", "开发教程",
         ["编程", "开发", "python", "java", "前端", "后端", "全栈", "部署"],
         [],
         "编程开发教程"),
        ("other-lesson", "其他教程",
         [],
         [],
         "其他教程/课程"),
    ],

    "virtual-cards": [
        ("depay", "Depay/OneKey",
         ["depay", "onekey"],
         [],
         "Depay/OneKey 虚拟卡"),
        ("wise", "Wise/Payoneer",
         ["wise", "payoneer"],
         [],
         "Wise/Payoneer"),
        ("virtual-visa", "虚拟 Visa/万事达",
         ["visa", "万事达", "虚拟卡", "信用卡", "美国卡"],
         [],
         "虚拟信用卡"),
    ],

    "gcp": [
        ("gcp-account", "GCP 账号",
         ["账号", "300", "赠金"],
         [],
         "GCP 账号含赠金"),
        ("gcp-other", "GCP 其他",
         [],
         [],
         "GCP 其他服务"),
    ],

    "proxy-vpn": [
        ("vpn-node", "机场/节点",
         ["机场", "节点", "专线"],
         [],
         "机场节点订阅"),
        ("vpn-tool", "VPN 工具",
         ["vpn", "v2ray", "clash", "trojan", "vmess", "hysteria", "ssr"],
         [],
         "VPN 客户端/工具"),
        ("vps", "VPS/服务器",
         ["vps", "服务器", "主机"],
         [],
         "VPS 云服务器"),
    ],

    "apple-misc": [
        ("trial-card", "苹果体验卡",
         ["体验卡", "天卡", "苹果卡密", "吃丹", "首富"],
         [],
         "苹果体验卡/天卡"),
        ("shadowrocket", "小火箭/代理",
         ["小火箭", "shadowrocket", "quantum", "surge", "stash", "loon"],
         [],
         "小火箭等代理工具"),
    ],
}


def _text(item: NormItem) -> str:
    parts = [item.title, item.description, item.category_raw]
    return ' '.join(p for p in parts if p).lower()


def classify_subtype(item: NormItem, type_slug: str) -> tuple[str, str, str]:
    """
    返回 (subtype_slug, subtype_name, method)
    method: 'rule' | 'fallback'
    """
    rules = SUBTYPE_RULES.get(type_slug, [])
    if not rules:
        return (type_slug + '-other', '其他/待AI归类', 'fallback')

    text = _text(item)
    for slug, name, inc, exc, desc in rules:
        if any(kw.lower() in text for kw in inc):
            if not exc or not any(ek.lower() in text for ek in exc):
                return (slug, name, 'rule')

    return (type_slug + '-other', '其他/待AI归类', 'fallback')
