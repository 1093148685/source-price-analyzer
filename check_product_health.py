#!/usr/bin/env python3
"""
Product Health Checker — 验证商品链接可达性 & 价格一致性
通过 API 重抓数据，与缓存对比，检测：
  1. 商品是否仍然存在
  2. 价格是否变动
  3. 哪些店铺已无商品

Usage: python3 check_product_health.py [--report]
  --report  输出人类可读报告（默认输出 JSON）
"""

import os, sys, json, time, statistics
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, 'data')
CACHE_FILE = os.path.join(DATA_DIR, 'cache_v2.json')
REPORT_FILE = os.path.join(DATA_DIR, 'health_report.json')

# Import app module functions
sys.path.insert(0, APP_DIR)
from app import session, refresh_acw_cookie, login, fetch_all_goods, fetch_merchants, normalize


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    with open(CACHE_FILE) as f:
        return json.load(f)


def build_item_index(products):
    """Build index of items by their unique key for comparison."""
    index = {}
    for p in products:
        for it in p.get('items', []):
            key = str(it.get('id', '')) or it.get('title', '')
            index[key] = {
                'title': it.get('title', ''),
                'price': it.get('price', 0),
                'shop_name': it.get('shop_name', ''),
                'shop_id': it.get('shop_id', ''),
                'product_slug': p.get('slug', ''),
                'product_name': p.get('name', ''),
                'link': it.get('link', ''),
                'trusted': it.get('trusted', True),
            }
    return index


def check_health():
    cache = load_cache()
    if not cache:
        return {'ok': False, 'error': 'No cache file found'}

    # Build index of cached items
    old_index = build_item_index(cache.get('products', []))
    old_shop_ids = set(v['shop_id'] for v in old_index.values() if v['shop_id'])
    
    # Fetch fresh data
    print("Fetching fresh goods data...", file=sys.stderr)
    s = session()
    refresh_acw_cookie(s)
    login(s)
    
    fresh_goods, total = fetch_all_goods(s)
    fresh_merchants, m_total = fetch_merchants(s)
    
    print(f"Fetched {len(fresh_goods)} goods from {m_total} merchants", file=sys.stderr)
    
    # Build index of fresh items (by ID)
    fresh_index = {}
    for g in fresh_goods:
        key = str(g.get('id', ''))
        fresh_index[key] = {
            'title': g.get('title', ''),
            'price': g.get('price', 0),
            'shop_name': g.get('shop_name', ''),
            'shop_id': g.get('shop_id', ''),
            'link': g.get('link', ''),
        }
    
    # Build fresh shop index
    fresh_shop_ids = {m.get('agent_key', '') for m in fresh_merchants if m.get('agent_key')}
    
    # ── Comparison ──
    gone_items = []        # Items in cache but not in fresh data
    price_changes = []     # Items with price differences
    new_items = []         # Items in fresh data but not in cache
    
    for key, old in old_index.items():
        if key not in fresh_index:
            gone_items.append(old)
        else:
            fresh = fresh_index[key]
            if abs(old['price'] - fresh['price']) > 0.01:
                price_changes.append({
                    'title': old['title'],
                    'shop_name': old['shop_name'],
                    'old_price': old['price'],
                    'new_price': fresh['price'],
                    'diff': round(fresh['price'] - old['price'], 2),
                    'product': old['product_name'],
                    'link': fresh.get('link', ''),
                })
    
    for key, fresh in fresh_index.items():
        if key not in old_index:
            new_items.append(fresh)
    
    # Check shops with no products
    empty_shops = old_shop_ids - fresh_shop_ids
    # Shops that exist but have very few goods
    merchant_goods_count = {}
    for g in fresh_goods:
        sid = g.get('shop_id', '')
        merchant_goods_count[sid] = merchant_goods_count.get(sid, 0) + 1
    
    low_stock_shops = [
        {'shop_id': sid, 'shop_name': '', 'count': c}
        for sid, c in merchant_goods_count.items()
        if c <= 1
    ]
    
    report = {
        'ts': time.time(),
        'datetime': datetime.now().isoformat(),
        'summary': {
            'cached_items': len(old_index),
            'fresh_items': len(fresh_index),
            'gone_count': len(gone_items),
            'price_changed_count': len(price_changes),
            'new_items_count': len(new_items),
            'empty_shops_count': len(empty_shops),
            'low_stock_shops_count': len(low_stock_shops),
        },
        'gone_items': gone_items[:200],
        'price_changes': sorted(price_changes, key=lambda x: abs(x['diff']), reverse=True)[:200],
        'empty_shop_ids': list(empty_shops)[:200],
        'low_stock_shops': low_stock_shops[:200],
    }
    
    # Save report
    with open(REPORT_FILE, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report


def format_report(report):
    """Generate human-readable report."""
    s = report['summary']
    lines = []
    lines.append(f"## 商品健康检测报告")
    lines.append(f"检测时间: {report['datetime']}")
    lines.append(f"")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 缓存商品数 | {s['cached_items']} |")
    lines.append(f"| 当前在线商品数 | {s['fresh_items']} |")
    lines.append(f"| 已下架商品 | {s['gone_count']} |")
    lines.append(f"| 价格变动商品 | {s['price_changed_count']} |")
    lines.append(f"| 新增商品 | {s['new_items_count']} |")
    lines.append(f"| 无商品的店铺 | {s['empty_shops_count']} |")
    lines.append(f"| 仅1件商品的店铺 | {s['low_stock_shops_count']} |")
    lines.append(f"")
    
    if report['price_changes']:
        lines.append(f"### 价格变动 (前 20 条)")
        lines.append(f"")
        for pc in report['price_changes'][:20]:
            arrow = '↑' if pc['diff'] > 0 else '↓' if pc['diff'] < 0 else '→'
            lines.append(f"- {arrow} ¥{pc['old_price']} → ¥{pc['new_price']} ({pc['diff']:+.2f}) | {pc['title'][:40]} | {pc['shop_name']} | [{pc['product']}]")
        lines.append(f"")
    
    if report['gone_items']:
        lines.append(f"### 已下架商品 (前 20 条)")
        lines.append(f"")
        for gi in report['gone_items'][:20]:
            lines.append(f"- {gi['title'][:50]} | {gi['shop_name']} | ¥{gi['price']} | [{gi['product_name']}]")
        lines.append(f"")
    
    return '\n'.join(lines)


if __name__ == '__main__':
    report = check_health()
    if '--report' in sys.argv:
        print(format_report(report))
    else:
        print(json.dumps(report['summary'], ensure_ascii=False))
    
    # Exit with warning if issues found
    s = report['summary']
    if s['gone_count'] > 20 or s['price_changed_count'] > 20:
        sys.exit(2)  # Signal: significant changes
    elif s['gone_count'] > 0 or s['price_changed_count'] > 0:
        sys.exit(1)  # Signal: some changes
    else:
        sys.exit(0)  # All good
