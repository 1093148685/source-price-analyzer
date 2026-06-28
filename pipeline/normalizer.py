"""
Normalizer — 将各数据源原始 JSON 转为统一的 NormItem。

通过 SOURCE_MAPPINGS 配置字段映射，新增数据源只需加配置。
"""
import re, html, time
from typing import Any
from .schema import NormItem

# ── 工具函数 ──

def _money(v: Any) -> float:
    try: return float(v or 0)
    except: return 0.0

def _clean(s: Any) -> str:
    s = html.unescape(str(s or ''))
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def _nested_get(d: dict, path: str, default=None):
    """支持 'shop.nickname' 点号嵌套取值"""
    keys = path.split('.')
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k)
        else:
            return default
        if d is None:
            return default
    return d

def _first_of(d: dict, fields: tuple, default=""):
    """取 fields 中第一个非空值"""
    for f in fields:
        v = _nested_get(d, f)
        if v is not None and str(v).strip():
            return str(v).strip()
    return str(default)

def _first_float(d: dict, fields: tuple, default=0.0) -> float:
    for f in fields:
        v = _nested_get(d, f)
        if v is not None and float(v or 0) > 0:
            return float(v)
    return float(default)


# ── 数据源字段映射配置 ──
# 格式: { source_name: { norm_field: (候选字段1, 候选字段2, ...) } }
# NormItem 字段名 → 原始 JSON 中候选字段路径列表（按优先级）

SOURCE_MAPPINGS: dict[str, dict[str, tuple]] = {
    "ldxp": {
        "source_id":      ("id", "goods_key", "goods_id", "goodsId", "link"),
        "title":          ("name", "title", "goods_name"),
        "description":    ("description", "desc", "subtitle"),
        "price":          ("price", "agent_price3", "agent_price2", "agent_price1", "cost_price", "sale_price", "selling_price"),
        "stock":          ("stock_count", "stock", "inventory"),
        "supplier_id":    ("shop.agent_key", "shop.id", "shop_id", "merchant_id"),
        "supplier_name":  ("shop.nickname", "shop.name", "shop_name", "merchant_name"),
        "category_raw":   ("category.name", "category_name", "tag_name", "group_name"),
        "url":            ("link",),
        "status":         ("status",),
    },
}


def extract_raw_items(raw: dict, source: str = "ldxp") -> list[dict]:
    """从 API 响应中提取原始 item 列表"""
    data = raw.get('data', raw)
    if isinstance(data, dict):
        for k in ['list', 'data', 'rows', 'items']:
            if isinstance(data.get(k), list):
                data = data[k]
                break
    if not isinstance(data, list):
        return []
    return data


def normalize_item(raw: dict, source: str = "ldxp", fetched_at: float | None = None) -> NormItem | None:
    """将单个原始 item dict 转为 NormItem"""
    mapping = SOURCE_MAPPINGS.get(source)
    if not mapping:
        raise ValueError(f"Unknown source: {source}")

    # Extract shop_id from user.link if agent_key is missing
    shop = raw.get('shop') or raw.get('merchant') or raw.get('user') or {}
    shop_slug = ""
    sl = _clean(shop.get('link', ''))
    m = re.search(r'/shop/([^/\s?#]+)', sl)
    if m:
        shop_slug = m.group(1)

    raw['_shop_slug'] = shop_slug  # fallback supplier_id
    raw['shop'] = shop

    title = _clean(_first_of(raw, mapping['title']))
    if not title:
        return None

    item = NormItem(
        source=source,
        source_id=_clean(_first_of(raw, mapping['source_id'])),
        title=title,
        description=_clean(_first_of(raw, mapping.get('description', ('desc',))))[:420],
        price=_first_float(raw, mapping['price']),
        stock=int(float(_first_of(raw, mapping.get('stock', ('stock',)), 0))),
        status=int(float(_first_of(raw, mapping.get('status', ('status',)), 1))),
        supplier_id=_clean(_first_of(raw, mapping['supplier_id'])) or shop_slug,
        supplier_name=_clean(_first_of(raw, mapping['supplier_name'])),
        category_raw=_clean(_first_of(raw, mapping.get('category_raw', ('category',)))),
        url=_clean(_first_of(raw, mapping.get('url', ('link',)))),
        raw_data=raw,
        fetched_at=fetched_at or time.time(),
    )
    return item


def normalize(raw: dict, source: str = "ldxp") -> list[NormItem]:
    """批量标准化 — 兼容旧 app.py 的 normalize() 调用方式"""
    raw_items = extract_raw_items(raw, source)
    out = []
    for x in raw_items:
        item = normalize_item(x, source)
        if item:
            out.append(item)
    return out
