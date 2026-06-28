"""
Admin module — 安全检测、调度管理、认证
"""
import os, json, time, hashlib, secrets
from datetime import datetime
from typing import Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

APP_DIR = '/opt/data/apps/source-price-analyzer'
DATA_DIR = os.path.join(APP_DIR, 'data')
ADMIN_CONFIG_FILE = os.path.join(DATA_DIR, 'admin_config.json')
HEALTH_HISTORY_FILE = os.path.join(DATA_DIR, 'health_history.json')
CACHE_FILE = os.path.join(DATA_DIR, 'cache_v2.json')

# ── Scheduler ──
scheduler = BackgroundScheduler(daemon=True)

# ── Auth ──
def load_admin_config():
    defaults = {
        'password_hash': '',  # SHA256 hash
        'token': '',
        'health_schedule': {'enabled': False, 'cron': '0 3 * * *', 'timezone': 'Asia/Shanghai'},
    }
    if os.path.exists(ADMIN_CONFIG_FILE):
        try:
            with open(ADMIN_CONFIG_FILE) as f:
                cfg = json.load(f)
                defaults.update(cfg)
        except Exception:
            pass
    return defaults

def save_admin_config(cfg):
    with open(ADMIN_CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def verify_admin_token(token: str) -> bool:
    cfg = load_admin_config()
    return bool(token) and token == cfg.get('token', '')

def admin_login(password: str) -> str | None:
    """Returns token if password correct."""
    cfg = load_admin_config()
    if not cfg.get('password_hash'):
        return None
    if hash_password(password) == cfg['password_hash']:
        token = secrets.token_hex(32)
        cfg['token'] = token
        save_admin_config(cfg)
        return token
    return None

def admin_setup(password: str) -> str:
    """Initial setup — set admin password, return token."""
    cfg = load_admin_config()
    cfg['password_hash'] = hash_password(password)
    token = secrets.token_hex(32)
    cfg['token'] = token
    save_admin_config(cfg)
    return token

def admin_logout():
    cfg = load_admin_config()
    cfg['token'] = ''
    save_admin_config(cfg)


# ── Health Check ──
def load_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    with open(CACHE_FILE) as f:
        return json.load(f)

def load_health_history():
    if os.path.exists(HEALTH_HISTORY_FILE):
        try:
            with open(HEALTH_HISTORY_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_health_history(history):
    # Keep last 50 entries
    history = history[-50:]
    with open(HEALTH_HISTORY_FILE, 'w') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def build_item_index(products):
    index = {}
    for p in products:
        for it in p.get('items', []):
            # 用 (id, title, shop_id) 三元组做 key，与下面 fresh_index 保持一致
            key = f"{it.get('id', '')}|{it.get('title', '')}|{it.get('shop_id', '')}"
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

# ── Progress Tracking ──
_health_progress: dict[str, Any] = {'running': False, 'step': '', 'message': '', 'started_at': 0}

def _set_progress(step: str, message: str):
    global _health_progress
    _health_progress = {'running': True, 'step': step, 'message': message, 'started_at': time.time()}
    # Also write to file so it survives process check
    with open(os.path.join(DATA_DIR, 'health_progress.json'), 'w') as f:
        json.dump(_health_progress, f)

def _clear_progress():
    global _health_progress
    _health_progress = {'running': False, 'step': 'done', 'message': '检测完成', 'started_at': 0}
    with open(os.path.join(DATA_DIR, 'health_progress.json'), 'w') as f:
        json.dump(_health_progress, f)

def get_health_progress() -> dict:
    return _health_progress

def run_health_check() -> dict:
    """Execute full health check, save to history, return report."""
    from app import session, refresh_acw_cookie, login, fetch_all_goods, fetch_merchants

    _set_progress('loading_cache', '加载缓存数据...')
    cache = load_cache()
    if not cache:
        _clear_progress()
        return {'ok': False, 'error': 'No cache file'}

    _set_progress('indexing', f"构建商品索引 ({len(cache.get('products', []))} 个产品)...")
    old_index = build_item_index(cache.get('products', []))
    old_shop_ids = set(v['shop_id'] for v in old_index.values() if v['shop_id'])

    _set_progress('login', '登录货源平台...')
    s = session()
    refresh_acw_cookie(s)
    login(s)

    _set_progress('fetching_goods', '正在拉取全量商品数据...')
    fresh_goods, total = fetch_all_goods(s)
    _set_progress('fetching_merchants', f'正在拉取商家数据 (已获取 {len(fresh_goods)} 件商品)...')
    fresh_merchants, m_total = fetch_merchants(s)

    _set_progress('comparing', f'对比 {len(old_index)} 缓存 vs {len(fresh_goods)} 在线商品...')

    fresh_index = {}
    for g in fresh_goods:
        gid = str(g.get('id', ''))
        gtitle = g.get('title', '')
        gshop = str(g.get('shop_id', ''))
        key = f"{gid}|{gtitle}|{gshop}"
        fresh_index[key] = {
            'title': g.get('title', ''),
            'price': g.get('price', 0),
            'shop_name': g.get('shop_name', ''),
            'shop_id': g.get('shop_id', ''),
            'link': g.get('link', ''),
            'status': int(g.get('status') or 1),
        }

    fresh_shop_ids = {m.get('agent_key', '') for m in fresh_merchants if m.get('agent_key')}

    gone_items = []
    price_changes = []
    delisted_items = []

    for key, old in old_index.items():
        if key not in fresh_index:
            gone_items.append(old)
        else:
            fresh = fresh_index[key]
            if fresh.get('status') == 0:
                delisted_items.append(old)
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

    empty_shops = old_shop_ids - fresh_shop_ids
    merchant_goods_count = {}
    for g in fresh_goods:
        sid = g.get('shop_id', '')
        merchant_goods_count[sid] = merchant_goods_count.get(sid, 0) + 1

    low_stock_shops = [
        {'shop_id': sid, 'count': c}
        for sid, c in merchant_goods_count.items() if c <= 1
    ]

    report = {
        'ts': time.time(),
        'datetime': datetime.now().isoformat(),
        'summary': {
            'cached_items': len(old_index),
            'fresh_items': len(fresh_index),
            'gone_count': len(gone_items),
            'delisted_count': len(delisted_items),
            'price_changed_count': len(price_changes),
            'new_items_count': len(fresh_index) - len(old_index) + len(gone_items),
            'empty_shops_count': len(empty_shops),
            'low_stock_shops_count': len(low_stock_shops),
        },
        'gone_items': gone_items[:100],
        'delisted_items': delisted_items[:100],
        'price_changes': sorted(price_changes, key=lambda x: abs(x['diff']), reverse=True)[:100],
        'empty_shop_ids': list(empty_shops)[:100],
        'low_stock_shops': low_stock_shops[:100],
    }

    # Save to history
    history = load_health_history()
    history.append(report)
    save_health_history(history)

    _clear_progress()
    return report


# ── Scheduler Management ──
_health_job_id = 'admin_health_check'

def start_health_scheduler():
    cfg = load_admin_config()
    hs = cfg.get('health_schedule', {})
    if not hs.get('enabled'):
        return False
    cron_expr = hs.get('cron', '0 19 * * *')
    tz = hs.get('timezone', 'Asia/Shanghai')
    try:
        if scheduler.get_job(_health_job_id):
            scheduler.remove_job(_health_job_id)
        scheduler.add_job(
            run_health_check,
            CronTrigger.from_crontab(cron_expr, timezone=tz),
            id=_health_job_id,
            replace_existing=True,
        )
        if not scheduler.running:
            scheduler.start()
        return True
    except Exception as e:
        return False

def stop_health_scheduler():
    if scheduler.get_job(_health_job_id):
        scheduler.remove_job(_health_job_id)

def update_health_schedule(enabled: bool, cron_expr: str = '0 19 * * *', timezone: str = 'Asia/Shanghai'):
    cfg = load_admin_config()
    cfg['health_schedule'] = {'enabled': enabled, 'cron': cron_expr, 'timezone': timezone}
    save_admin_config(cfg)
    if enabled:
        return start_health_scheduler()
    else:
        stop_health_scheduler()
        return True

def get_schedule_status():
    cfg = load_admin_config()
    hs = cfg.get('health_schedule', {})
    job = scheduler.get_job(_health_job_id)
    return {
        'enabled': hs.get('enabled', False),
        'cron': hs.get('cron', '0 19 * * *'),
        'timezone': hs.get('timezone', 'Asia/Shanghai'),
        'next_run': job.next_run_time.isoformat() if job and job.next_run_time else None,
        'running': bool(job),
    }
