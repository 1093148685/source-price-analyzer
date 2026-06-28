"""
Product Detector — 产品大类识别（评分制）。

替代旧 PRODUCT_TYPES 的简单 include/exclude 逻辑。
用关键词匹配评分 + 反关键词扣分，选最高分产品类型。
"""
from typing import Any
from ..schema import NormItem

# ── 产品定义 ──
# 每个产品类型: keywords 匹配加分, anti_keywords 匹配扣分, priority 用于同分优先级

PRODUCT_DEFINITIONS = [
    {
        "slug": "chatgpt",
        "name": "ChatGPT",
        "vendor": "OpenAI",
        "emoji": "🤖",
        "keywords": ["chatgpt", "gpt", "openai", "chat gpt", "plus成品", "plus账号", "plus月卡", "plus 成品", "plus 账号", "gpt-plus", "chatgpt-plus", "chatgpt plus", "gpt plus", "plus"],
        "anti_keywords": [
            "claude", "grok", "supergrok", "gemini", "netflix", "奈飞",
            "夸克", "百度网盘", "云盘", "apple id", "icloud", "苹果id", "苹果账号", "itunes",
            "hotmail", "outlook",  # 纯邮箱产品，不是 GPT
        ],
        "keyword_weight": 1.0,
        "anti_weight": 2.0,
        "priority": 10,
        "desc": "ChatGPT Plus、Pro、Free、Team 会员与账号",
    },
    {
        "slug": "codex-api",
        "name": "Codex / API",
        "vendor": "OpenAI",
        "emoji": "🔑",
        "keywords": ["codex", "接码", "api中转", "api反代", "openai api", "openai key", "api key", "api额度", "paypal接码", "cursor接码", "gojek接码", "cursor"],
        "anti_keywords": [
            "chatgpt plus", "gpt plus", "chatgpt pro", "gpt pro",
            "claude pro", "claude max", "grok super", "netflix", "奈飞",
            "夸克", "百度网盘", "apple id", "hotmail", "outlook",
        ],
        "keyword_weight": 1.0,
        "anti_weight": 1.5,
        "priority": 10,  # 与 ChatGPT 同级，防抢
        "desc": "OpenAI Codex、API Key/Token、接码、中转反代额度",
    },
    {
        "slug": "microsoft-email",
        "name": "微软邮箱",
        "vendor": "Microsoft",
        "emoji": "📧",
        "keywords": ["hotmail", "outlook", "微软邮箱", "空邮箱", "全新邮箱", "邮箱换绑", "邮箱交付", "邮箱账号", "hotmail邮箱", "outlook邮箱"],
        "anti_keywords": [
            "gmail", "谷歌邮箱", "google邮箱", "apple id", "icloud",
            "netflix", "奈飞", "夸克", "百度网盘", "游戏", "王者", "吃鸡", "pubg", "原神",
            # 注意：不排除 gpt/plus！邮箱为交付方式的 GPT 产品应同时匹配两个类别
        ],
        "keyword_weight": 1.0,
        "anti_weight": 1.0,
        "priority": 5,  # 低优先级：GPT+邮箱 优先归 ChatGPT
        "desc": "Hotmail、Outlook 微软邮箱账号",
    },
    {
        "slug": "claude",
        "name": "Claude",
        "vendor": "Anthropic",
        "emoji": "🧠",
        "keywords": ["claude"],
        "anti_keywords": [
            "chatgpt", "gpt plus", "gpt pro", "grok", "gemini",
            "netflix", "奈飞", "codex", "接码", "api中转", "api key",
        ],
        "keyword_weight": 1.0,
        "anti_weight": 1.5,
        "priority": 8,
        "desc": "Claude Pro、Max、Team、账号",
    },
    {
        "slug": "grok",
        "name": "Grok",
        "vendor": "xAI",
        "emoji": "𝕏",
        "keywords": ["grok", "supergrok", "super grok"],
        "anti_keywords": [
            "chatgpt", "gpt plus", "gpt pro", "claude", "gemini",
            "netflix", "奈飞", "codex", "接码", "api",
        ],
        "keyword_weight": 1.0,
        "anti_weight": 1.5,
        "priority": 7,
        "desc": "Grok / SuperGrok 会员账号",
    },
    {
        "slug": "netflix",
        "name": "Netflix / 奈飞",
        "vendor": "Netflix",
        "emoji": "🎬",
        "keywords": ["netflix", "奈飞"],
        "anti_keywords": ["chatgpt", "claude", "grok", "夸克", "百度网盘", "apple id"],
        "keyword_weight": 1.0,
        "anti_weight": 1.0,
        "priority": 6,
        "desc": "奈飞账号、车位",
    },
    {
        "slug": "cloud-drive",
        "name": "网盘 / 云盘",
        "vendor": "多平台",
        "emoji": "☁️",
        "keywords": ["网盘", "夸克", "百度网盘", "云盘"],
        "anti_keywords": ["chatgpt", "claude", "grok", "netflix", "奈飞", "apple id"],
        "keyword_weight": 1.0,
        "anti_weight": 1.0,
        "priority": 4,
        "desc": "百度网盘、夸克网盘",
    },
    {
        "slug": "apple",
        "name": "Apple ID / 苹果",
        "vendor": "Apple",
        "emoji": "🍎",
        "keywords": ["apple id", "苹果id", "苹果账号", "icloud", "苹果", "apple"],
        "anti_keywords": [
            "chatgpt", "claude", "grok", "netflix", "奈飞",
            "夸克", "百度网盘", "云盘", "地铁", "游戏", "吃鸡", "王者", "pubg", "原神", "和平精英",
        ],
        "keyword_weight": 1.0,
        "anti_weight": 1.5,
        "priority": 3,
        "desc": "Apple ID、iCloud",
    },
    {
        "slug": "gemini",
        "name": "Gemini",
        "vendor": "Google",
        "emoji": "💎",
        "keywords": ["gemini", "google gemini", "gemini pro", "gemini advanced", "gemini 2.5", "gemini 2.0"],
        "anti_keywords": [
            "chatgpt", "gpt", "claude", "grok", "netflix", "奈飞",
            "夸克", "百度网盘", "apple id", "codex", "cursor",
        ],
        "keyword_weight": 1.0,
        "anti_weight": 1.5,
        "priority": 8,
        "desc": "Google Gemini 会员账号与 API",
    },
    {
        "slug": "cursor",
        "name": "Cursor",
        "vendor": "Cursor Inc",
        "emoji": "🖱️",
        "keywords": ["cursor", "cursor pro", "cursor接码", "cusor", "cursor成品"],
        "anti_keywords": [
            "chatgpt", "gpt plus", "claude", "grok", "netflix", "奈飞",
        ],
        "keyword_weight": 1.0,
        "anti_weight": 1.5,
        "priority": 8,
        "desc": "Cursor IDE Pro 订阅与接码",
    },
    {
        "slug": "dev-tools",
        "name": "开发工具/AI IDE",
        "vendor": "多平台",
        "emoji": "🛠️",
        "keywords": ["windsurf", "devin", "lovart", "lovable", "replit", "bolt", "v0 dev", "cursory",
                     "github copilot", "copilot", "tabnine", "cody"],
        "anti_keywords": [
            "chatgpt plus", "gpt plus", "claude pro", "grok super", "netflix", "奈飞",
        ],
        "keyword_weight": 1.0,
        "anti_weight": 1.0,
        "priority": 7,
        "desc": "Windsurf、Devin、Copilot 等 AI 开发工具",
    },
    {
        "slug": "lessons",
        "name": "教程/课程",
        "vendor": "多平台",
        "emoji": "📚",
        "keywords": ["教程", "课程", "教学", "小白", "使用教程", "保姆级", "入门", "指南"],
        "anti_keywords": [
            "成品号", "直充", "代充", "接码", "api", "key", "token",
        ],
        "keyword_weight": 0.5,  # 低权重，防止教程类抢商品
        "anti_weight": 2.0,
        "priority": 2,
        "desc": "AI 使用教程、课程、教学指南",
    },
    {
        "slug": "virtual-cards",
        "name": "虚拟卡/支付",
        "vendor": "多平台",
        "emoji": "💳",
        "keywords": ["虚拟卡", "visa卡", "万事达", "信用卡", "depay", "onekey", "wise", "payoneer",
                     "stripe", "美国卡", "虚拟信用卡"],
        "anti_keywords": [
            "chatgpt", "gpt", "claude", "grok", "netflix", "奈飞",
        ],
        "keyword_weight": 1.0,
        "anti_weight": 1.0,
        "priority": 6,
        "desc": "虚拟信用卡、支付工具",
    },
    {
        "slug": "gcp",
        "name": "Google Cloud",
        "vendor": "Google",
        "emoji": "☁️",
        "keywords": ["gcp", "google cloud", "google cloud platform", "gcp账号", "gcp 300", "google cloud 300"],
        "anti_keywords": [
            "chatgpt", "gpt", "claude", "grok", "netflix", "奈飞",
        ],
        "keyword_weight": 1.0,
        "anti_weight": 1.0,
        "priority": 5,
        "desc": "Google Cloud Platform 账号与赠金",
    },
    {
        "slug": "proxy-vpn",
        "name": "代理/VPN/机场",
        "vendor": "多平台",
        "emoji": "🌐",
        "keywords": ["机场", "节点", "vpn", "vps", "代理", "翻墙", "科学上网", "中转", "专线",
                     "trojan", "vmess", "ssr", "clash", "v2ray", "hysteria"],
        "anti_keywords": [
            "chatgpt", "gpt", "claude", "grok", "netflix", "codex", "接码",
        ],
        "keyword_weight": 1.0,
        "anti_weight": 1.0,
        "priority": 4,
        "desc": "VPN、机场、代理节点",
    },
    {
        "slug": "apple-misc",
        "name": "苹果杂项/体验",
        "vendor": "Apple",
        "emoji": "🎫",
        "keywords": ["体验卡", "天卡", "苹果卡密", "一键吃丹", "一键首富", "小火箭", "shadowrocket",
                     "quantum", "surge", "stash", "loon"],
        "anti_keywords": [
            "chatgpt", "claude", "grok", "netflix", "奈飞",
        ],
        "keyword_weight": 1.0,
        "anti_weight": 1.0,
        "priority": 3,
        "desc": "苹果体验卡、小火箭、代理工具",
    },
]


def _text(item: NormItem) -> str:
    """组合搜索文本"""
    parts = [item.title, item.description, item.category_raw]
    return ' '.join(p for p in parts if p).lower()


def detect_product(item: NormItem) -> list[dict]:
    """
    返回所有匹配的产品类型及其评分，按评分降序排列。
    
    每项: {"slug": ..., "name": ..., "score": float, "matched_kw": [...], "matched_anti": [...]}
    """
    text = _text(item)
    results = []
    
    for pd in PRODUCT_DEFINITIONS:
        matched_kw = [kw for kw in pd["keywords"] if kw.lower() in text]
        matched_anti = [ak for ak in pd.get("anti_keywords", []) if ak.lower() in text]
        
        if not matched_kw:
            continue  # 完全没匹配关键词，跳过此类型
        
        score = len(matched_kw) * pd.get("keyword_weight", 1.0) - len(matched_anti) * pd.get("anti_weight", 1.0)
        
        results.append({
            "slug": pd["slug"],
            "name": pd["name"],
            "vendor": pd.get("vendor", ""),
            "emoji": pd.get("emoji", ""),
            "priority": pd.get("priority", 0),
            "score": score,
            "matched_kw": matched_kw,
            "matched_anti": matched_anti,
        })
    
    # 按 score 降序 → priority 降序
    results.sort(key=lambda x: (x["score"], x["priority"]), reverse=True)
    return results


def classify_product(item: NormItem) -> tuple[str, str, float]:
    """
    返回 (type_slug, type_name, confidence)
    评分 <= 0 的视为不确定，返回 ('unknown', '未分类', 0.0)
    """
    matches = detect_product(item)
    if not matches:
        return ('unknown', '未分类', 0.0)
    
    best = matches[0]
    if best["score"] <= 0:
        return ('unknown', '未分类', 0.0)
    
    confidence = min(1.0, max(0.1, best["score"] / 3.0))
    return (best["slug"], best["name"], confidence)
