"""
Pipeline Schema — 统一数据模型。

所有 Connector 输出 RawItem → Normalizer 转为 NormItem → 下游阶段消费。
"""
from dataclasses import dataclass, field, asdict
from typing import Any
import json, time


@dataclass
class NormItem:
    """标准化商品条目 — pipeline 内部通用格式"""
    # ── 唯一标识 ──
    source_id: str          # 原始平台商品ID
    source: str             # 数据来源标识 (ldxp, api_xxx, csv_xxx)

    # ── 商品信息 ──
    title: str
    description: str = ""
    price: float = 0.0      # 统一 CNY
    currency: str = "CNY"
    stock: int = 0
    status: int = 1         # 1=在售 0=下架

    # ── 商家信息 ──
    supplier_id: str = ""
    supplier_name: str = ""
    supplier_url: str = ""

    # ── 原始分类 ──
    category_raw: str = ""

    # ── 链接 ──
    url: str = ""

    # ── 管道标记 (后续阶段填充) ──
    type_slug: str = ""           # 产品大类 slug
    subtype_slug: str = ""        # 子类 slug
    entity_key: str = ""          # 去重实体 key
    quality_score: float = 0.0    # 0-100
    classify_method: str = ""     # rule / ai / fallback
    classify_confidence: float = 0.0  # 0-1

    # ── 元数据 ──
    raw_data: dict | None = None  # 保留原始 JSON
    fetched_at: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        # 不序列化 raw_data (太大)
        d.pop('raw_data', None)
        return d

    def to_legacy(self) -> dict:
        """转为旧 app.py 兼容格式 (给现有 API 用)"""
        return {
            'id': self.source_id,
            'title': self.title,
            'desc': self.description,
            'price': self.price,
            'stock': self.stock,
            'shop_name': self.supplier_name,
            'shop_id': self.supplier_id,
            'category': self.category_raw,
            'link': self.url,
            'status': self.status,
            'trusted': self.quality_score >= 50,
            'product_slug': self.subtype_slug or self.type_slug,
            'product_name': '',
            'type_slug': self.type_slug,
            'classify_method': self.classify_method,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'NormItem':
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class PipelineResult:
    """管道完整输出"""
    items: list[NormItem] = field(default_factory=list)
    source_stats: dict = field(default_factory=dict)
    types: list[dict] = field(default_factory=list)
    products: list[dict] = field(default_factory=list)
    ts: float = 0.0

    def to_legacy(self) -> dict:
        """转为旧 cache_v2.json 格式"""
        return {
            'ts': self.ts,
            'source': self.source_stats,
            'merchants': [],
            'source_items': [it.to_legacy() for it in self.items],
            'types': self.types,
            'products': self.products,
            'all_items': [it.to_legacy() for it in self.items],
            'ai_config': {'mode': 'pipeline-v1', 'note': '管道模式: 采集→标准化→分类→去重→质检→排序→输出'},
        }
