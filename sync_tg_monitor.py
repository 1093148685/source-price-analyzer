#!/usr/bin/env python3
"""Sync source-price-analyzer LDXP scan cache into TG Monitor product monitor tables.

Writes into TG Monitor existing tables:
- ldxp_shops
- ldxp_products
- ldxp_product_price_snapshots

The importer runs inside tg-monitor-app so it reuses TG Monitor's SQLAlchemy config.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent
CACHE_FILE = APP_DIR / "data" / "cache_v2.json"
STATUS_FILE = APP_DIR / "data" / "tg_sync_status.json"
CONTAINER = os.getenv("TG_MONITOR_CONTAINER", "tg-monitor-app")


def clean(v: Any, limit: int | None = None) -> str:
    import html, re
    s = html.unescape(str(v or ""))
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit] if limit else s


def num(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def integer(v: Any) -> int | None:
    try:
        if v is None or v == "":
            return None
        return int(float(v))
    except Exception:
        return None


def safe_token(value: Any, fallback: Any = '') -> str:
    raw = clean(value or fallback, 120)
    import re
    if raw and re.fullmatch(r'[A-Za-z0-9_-]{2,80}', raw):
        return raw
    seed = raw or clean(fallback, 120) or 'unknown'
    return 'shop-' + hashlib.sha1(seed.encode('utf-8')).hexdigest()[:16]


def load_cache() -> dict[str, Any]:
    if not CACHE_FILE.exists():
        raise SystemExit(f"cache not found: {CACHE_FILE}")
    return json.loads(CACHE_FILE.read_text(encoding="utf-8"))


def build_payload(cache: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
    merchants: dict[str, dict[str, Any]] = {}
    for m in cache.get("merchants") or []:
        token = safe_token(m.get("agent_key") or m.get("shop_id"), m.get("shop_name") or m.get("title"))
        if not token:
            continue
        merchants[token.lower()] = {
            "token": token,
            "link": clean(m.get("link") or f"https://pay.ldxp.cn/shop/{token}", 500),
            "nickname": clean(m.get("shop_name") or token, 255),
            "description": clean(m.get("title"), 2000),
            "goods_count": integer(m.get("goods_count")) or 0,
            "category_count": 0,
            "sell_count": 0,
            "last_fetch_at": now,
        }

    products: list[dict[str, Any]] = []
    seen = set()
    source_items = cache.get("source_items") or cache.get("all_items") or []
    for it in source_items:
        token = safe_token(it.get("shop_id"), it.get("shop_name"))
        if not token:
            token = "unknown-shop"
        if token not in merchants:
            merchants[token.lower()] = {
                "token": token,
                "link": f"https://pay.ldxp.cn/shop/{token}",
                "nickname": clean(it.get("shop_name") or token, 255),
                "description": "从链动货源比价站全量扫描导入",
                "goods_count": 0,
                "category_count": 0,
                "sell_count": 0,
                "last_fetch_at": now,
            }
        key = clean(it.get("id") or f"{token}:{it.get('title')}:{it.get('price')}", 100)
        dedupe = (token, key)
        if dedupe in seen:
            continue
        seen.add(dedupe)
        raw = it.get("raw") if isinstance(it.get("raw"), dict) else {}
        products.append({
            "shop_token": token,
            "goods_key": key,
            "link": clean(it.get("link") or raw.get("link") or f"https://pay.ldxp.cn/item/{key}", 500),
            "goods_type": clean(raw.get("goods_type") or raw.get("type") or "card", 50),
            "name": clean(it.get("title"), 500),
            "price": num(it.get("price")),
            "market_price": num(raw.get("market_price") or raw.get("marketPrice")),
            "image": clean(raw.get("image") or raw.get("cover") or raw.get("pic"), 1000) or None,
            "category_id": integer((raw.get("category") or {}).get("id") if isinstance(raw.get("category"), dict) else raw.get("category_id")),
            "category_name": clean(it.get("product_name") or it.get("category") or it.get("type_slug"), 255),
            "stock_count": integer(it.get("stock")),
            "sales_count": integer(raw.get("sales_count") or raw.get("salesCount") or raw.get("sell_count") or raw.get("sales")),
            "limit_count": integer(raw.get("limit_count") or raw.get("limitCount")),
            "send_order": integer(raw.get("send_order") or raw.get("sendOrder")),
            "description_text": clean(it.get("desc"), 4000),
            "last_seen_at": now,
        })
    return {"generated_at": now, "source": cache.get("source") or {}, "shops": list(merchants.values()), "products": products}


IMPORTER = r'''
import json
import sys
from datetime import datetime
from sqlalchemy import select
from app.db import session_scope
from app.models import LdxpShop, LdxpProduct, LdxpProductPriceSnapshot

path=sys.argv[1]
payload=json.load(open(path,encoding='utf-8'))
now=datetime.utcnow().replace(minute=0,second=0,microsecond=0)
shops_in=payload.get('shops') or []
products_in=payload.get('products') or []
shop_count=product_count=snapshot_count=0
with session_scope() as db:
    shop_by_token={s.token.lower():s for s in db.execute(select(LdxpShop)).scalars().all()}
    for row in shops_in:
        token=str(row.get('token') or '').strip()[:100]
        if not token: continue
        lookup=token.lower()
        shop=shop_by_token.get(lookup)
        if not shop:
            shop=LdxpShop(token=token, link=row.get('link') or f'https://pay.ldxp.cn/shop/{token}')
            db.add(shop); db.flush(); shop_by_token[lookup]=shop
        shop.link=row.get('link') or shop.link
        shop.nickname=(row.get('nickname') or token)[:255]
        shop.description=row.get('description') or ''
        shop.last_error=None
        shop.last_fetch_at=datetime.utcnow()
        shop.updated_at=datetime.utcnow()
        shop_count+=1
    db.flush()
    products_by_shop={}
    for lookup,shop in shop_by_token.items():
        products_by_shop[lookup]={p.goods_key:p for p in db.execute(select(LdxpProduct).where(LdxpProduct.shop_id==shop.id)).scalars().all()}
    shop_stats={}
    for row in products_in:
        token=str(row.get('shop_token') or '').strip()[:100]
        key=str(row.get('goods_key') or '').strip()[:100]
        lookup=token.lower()
        if not token or not key or lookup not in shop_by_token: continue
        shop=shop_by_token[lookup]
        existing=products_by_shop.setdefault(lookup,{})
        product=existing.get(key)
        if not product:
            product=LdxpProduct(shop_id=shop.id, shop_token=shop.token, goods_key=key, link=row.get('link') or '', name=(row.get('name') or key)[:500])
            product.first_seen_at=datetime.utcnow()
            db.add(product); existing[key]=product
        product.shop_token=shop.token
        product.link=row.get('link') or product.link
        product.goods_type=(row.get('goods_type') or 'card')[:50]
        product.name=(row.get('name') or key)[:500]
        product.price=row.get('price')
        product.market_price=row.get('market_price')
        product.image=row.get('image')
        product.category_id=row.get('category_id')
        product.category_name=(row.get('category_name') or '')[:255]
        product.stock_count=row.get('stock_count')
        product.sales_count=row.get('sales_count')
        product.limit_count=row.get('limit_count')
        product.send_order=row.get('send_order')
        product.description_text=row.get('description_text') or ''
        product.last_seen_at=datetime.utcnow()
        product.updated_at=datetime.utcnow()
        db.flush()
        product_count+=1
        stats=shop_stats.setdefault(lookup, {'goods':0,'cats':set(),'sales':0})
        stats['goods']+=1
        stats['cats'].add(product.category_name or '未分类')
        stats['sales']+=int(product.sales_count or 0)
        exists=db.execute(select(LdxpProductPriceSnapshot.id).where(LdxpProductPriceSnapshot.product_id==product.id, LdxpProductPriceSnapshot.snapshot_at==now).limit(1)).scalar_one_or_none()
        if exists is None:
            db.add(LdxpProductPriceSnapshot(product_id=product.id, goods_key=product.goods_key, shop_id=product.shop_id, price=product.price, market_price=product.market_price, stock_count=product.stock_count, sales_count=product.sales_count, snapshot_at=now))
            snapshot_count+=1
    for lookup,stats in shop_stats.items():
        shop=shop_by_token[lookup]
        shop.goods_count=stats['goods']
        shop.category_count=len(stats['cats'])
        shop.sell_count=stats['sales']
        shop.last_fetch_at=datetime.utcnow()
        shop.updated_at=datetime.utcnow()
print(json.dumps({'ok':True,'shops':shop_count,'products':product_count,'snapshots_added':snapshot_count}, ensure_ascii=False))
'''


def run_sync() -> dict[str, Any]:
    payload = build_payload(load_cache())
    with tempfile.TemporaryDirectory() as td:
        local_payload = Path(td) / "source_price_ldxp_import.json"
        local_importer = Path(td) / "source_price_importer.py"
        local_payload.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        local_importer.write_text(IMPORTER, encoding="utf-8")
        subprocess.run(["docker", "cp", str(local_payload), f"{CONTAINER}:/tmp/source_price_ldxp_import.json"], check=True)
        subprocess.run(["docker", "cp", str(local_importer), f"{CONTAINER}:/tmp/source_price_importer.py"], check=True)
        proc = subprocess.run(["docker", "exec", CONTAINER, "bash", "-lc", "cd /app && PYTHONPATH=/app python3 /tmp/source_price_importer.py /tmp/source_price_ldxp_import.json"], text=True, capture_output=True, timeout=300)
        if proc.returncode != 0:
            raise RuntimeError((proc.stdout + "\n" + proc.stderr).strip())
        result = json.loads(proc.stdout.strip().splitlines()[-1])
    result.update({"generated_shops": len(payload["shops"]), "generated_products": len(payload["products"]), "synced_at": datetime.now().isoformat(timespec="seconds")})
    STATUS_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run_sync(), ensure_ascii=False, indent=2))
