"""
Pipeline Runner — 编排完整数据管道。

流程: Connector 采集 → Normalizer 标准化 → Classifier 分类 → Grouper 分组 → Exporter 输出
"""
import time, statistics
from typing import Any
from collections import defaultdict

from .schema import NormItem, PipelineResult
from .connectors.ldxp import session, refresh_acw_cookie, login, fetch_all_goods, fetch_merchants
from .classifier.product_detector import classify_product, PRODUCT_DEFINITIONS
from .classifier.subtype_classifier import classify_subtype


def _stat(items: list[NormItem]) -> dict:
    """统计摘要"""
    prices = sorted([it.price for it in items if 0 < it.price < 50000])
    shops = {it.supplier_id for it in items if it.supplier_id}
    return {
        'count': len(items),
        'shops': len(shops),
        'stock': sum(it.stock for it in items),
        'min': prices[0] if prices else 0,
        'max': prices[-1] if prices else 0,
        'avg': round(sum(prices) / len(prices), 2) if prices else 0,
        'median': statistics.median(prices) if prices else 0,
    }


def _assess_quality(item: NormItem) -> dict:
    """质检评分 (简化版，后续 Phase 4 完善)"""
    reasons = []
    if item.status == 0:
        reasons.append('商家已下架(未上架)')
    if item.price <= 0:
        reasons.append('无有效价格')
    trusted = len(reasons) == 0
    return {
        'trusted': trusted,
        'reasons': reasons,
        'label': '可信报价' if trusted else '疑似混入',
    }


def _sku_key(item: NormItem) -> str:
    """根据标题提取 SKU 标签"""
    text = (item.title + ' ' + item.description).lower()
    keys = []
    if any(x in text for x in ['官方', '正规', '直充', '充值', '卡密', 'cdk', 'ios', '菲区', '美区', '土区']):
        keys.append('官方充值/CDK')
    if any(x in text for x in ['成品号', '账号', '首登', '带rt', '非日抛']):
        keys.append('成品号')
    if any(x in text for x in ['日抛', '试用', '短期']):
        keys.append('短期/试用')
    if any(x in text for x in ['质保一个月', '质保30', '30天', '一个月', '月卡']):
        keys.append('月卡/30天')
    if any(x in text for x in ['无质保', '不质保']):
        keys.append('无质保')
    if any(x in text for x in ['质保']):
        keys.append('有质保')
    return ' · '.join(keys[:3]) or '标准货源'


def _build_product_groups(items: list[NormItem]) -> tuple[list[dict], list[dict]]:
    """
    将已分类的 NormItem 按 subtype_slug 分组，构造 products 和 types。
    返回 (types, products) — 兼容旧 API 格式。
    """
    # 按 type_slug 分组
    type_buckets: dict[str, dict] = {}
    for pd in PRODUCT_DEFINITIONS:
        type_buckets[pd['slug']] = {
            'slug': pd['slug'],
            'name': pd['name'],
            'vendor': pd.get('vendor', ''),
            'emoji': pd.get('emoji', ''),
            'desc': pd.get('desc', ''),
            'subtypes': defaultdict(list),
            'all_items': [],
        }

    for item in items:
        ts = item.type_slug
        if ts not in type_buckets:
            continue
        type_buckets[ts]['subtypes'][item.subtype_slug or ts + '-other'].append(item)
        type_buckets[ts]['all_items'].append(item)

    types = []
    products = []

    for ts, bucket in type_buckets.items():
        if not bucket['all_items']:
            continue

        type_products = []
        for ss, sitems in bucket['subtypes'].items():
            # 查找 subtype name
            from .classifier.subtype_classifier import SUBTYPE_RULES
            subtype_name = ss
            subtype_desc = ''
            for rule in SUBTYPE_RULES.get(ts, []):
                if rule[0] == ss:
                    subtype_name = rule[1]
                    subtype_desc = rule[4]
                    break

            # 附加质检
            for it in sitems:
                q = _assess_quality(it)
                it.quality_score = 100.0 if q['trusted'] else 20.0

            # 排序: 可信优先，价格升序
            sitems.sort(key=lambda x: (x.quality_score < 50, x.price))

            # SKU 分组
            sku_groups = defaultdict(list)
            for it in sitems:
                sku_groups[_sku_key(it)].append(it)

            skus = []
            for sku_name, sku_items in sku_groups.items():
                sku_items.sort(key=lambda x: (x.price <= 0, x.price))
                st = _stat(sku_items)
                shops = {it.supplier_id for it in sku_items}
                skus.append({
                    'key': sku_name, 'name': sku_name,
                    'items': [it.to_legacy() for it in sku_items],
                    'stats': st,
                    'shop_count': len([s for s in shops if s]),
                    'best': sku_items[0].to_legacy() if sku_items else None,
                })

            legacy_items = [it.to_legacy() for it in sitems]
            trusted_items = [it.to_legacy() for it in sitems if it.quality_score >= 50]
            product = {
                'slug': ss,
                'name': subtype_name,
                'desc': subtype_desc,
                'items': legacy_items,
                'skus': skus,
                'stats_all': _stat(sitems),
                'stats': _stat([it for it in sitems if it.quality_score >= 50]),
                'trusted_count': len(trusted_items),
                'suspicious_count': len(sitems) - len(trusted_items),
            }

            # 价格分布直方图
            source_items = [it for it in sitems if it.quality_score >= 50] or sitems
            prices = sorted([it.price for it in source_items if it.price > 0])
            if len(prices) >= 3:
                q1 = prices[len(prices) // 4]
                q3 = prices[3 * len(prices) // 4]
                iqr = q3 - q1
                upper = q3 + 3 * iqr if iqr > 0 else prices[-1]
                filtered = [p for p in prices if p <= upper]
                if len(filtered) >= 3 and filtered[-1] > filtered[0]:
                    nb = max(4, min(14, len(filtered) // 4))
                    bw = (filtered[-1] - filtered[0]) / nb
                    dist = []
                    for i in range(nb):
                        lo = filtered[0] + i * bw
                        hi = filtered[0] + (i + 1) * bw
                        cnt = sum(1 for p in filtered if lo - 0.001 <= p <= hi + 0.001)
                        dist.append({'lo': round(lo, 2), 'hi': round(hi, 2), 'count': cnt, 'pct': round(cnt / len(filtered) * 100, 1)})
                    product['price_distribution'] = {
                        'min': filtered[0], 'max': filtered[-1],
                        'median': statistics.median(filtered),
                        'buckets': dist, 'total': len(filtered),
                    }

            type_products.append(product)
            products.append(product)

        type_products.sort(key=lambda x: (x['stats']['count'] == 0, x['stats']['min'] or 999999))
        types.append({
            'slug': ts,
            'name': bucket['name'],
            'vendor': bucket.get('vendor', ''),
            'emoji': bucket.get('emoji', ''),
            'desc': bucket.get('desc', ''),
            'products': type_products,
            'stats': _stat(bucket['all_items']),
        })

    return types, products


def run_pipeline(force: bool = False) -> PipelineResult:
    """
    执行完整数据管道: 采集 → 标准化 → 分类 → 分组。
    返回 PipelineResult (含 to_legacy() 方法兼容旧 API)。
    """
    t0 = time.time()

    # Stage 1: 采集 + 标准化
    s = session()
    refresh_acw_cookie(s)
    login(s)
    items, total = fetch_all_goods(s)
    merchants, mtotal = fetch_merchants(s)

    # Stage 2: 分类
    for item in items:
        type_slug, type_name, confidence = classify_product(item)
        subtype_slug, subtype_name, method = classify_subtype(item, type_slug)
        item.type_slug = type_slug
        item.subtype_slug = subtype_slug
        item.classify_method = method
        item.classify_confidence = confidence
        # 在 to_legacy 中用到的字段
        item._type_name = type_name
        item._subtype_name = subtype_name

    # Stage 3: 分组 + 统计
    types, products = _build_product_groups(items)

    result = PipelineResult(
        items=items,
        source_stats={
            'mode': 'pipeline-v1',
            'total_goods_api': total,
            'fetched_goods': len(items),
            'total_merchants_api': mtotal,
            'fetched_merchants': len(merchants),
        },
        types=types,
        products=products,
        ts=time.time(),
    )

    return result
