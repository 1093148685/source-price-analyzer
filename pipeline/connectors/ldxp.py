"""
LDXP Connector — 链动小铺 (pay.ldxp.cn) 数据源连接器。

从 app.py 迁移 login/session/fetch_all_goods/fetch_merchants 逻辑。
"""
import os, json, time, requests
from ..normalizer import normalize_item


BASE = 'https://pay.ldxp.cn'
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(APP_DIR, 'data')
TOKEN_FILE=os.path.join(DATA_DIR, 'token.json')
USERNAME = os.getenv('LDXP_USERNAME', 'hugojin')
PASSWORD = os.getenv('LDXP_PASSWORD', '')
ESA_COOKIE = os.getenv('LDXP_ACW_SC_V2', '6a4007d7730ae78566fffb44cbf834f097d9e889')


def session():
    """创建带基础 cookie 的 requests Session"""
    s = requests.Session()
    s.cookies.set('acw_sc__v2', ESA_COOKIE, domain='pay.ldxp.cn')
    s.headers.update({
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json, text/plain, */*',
        'Referer': BASE + '/merchant/my_parent/source_square',
        'Origin': BASE,
    })
    tok = ''
    if os.path.exists(TOKEN_FILE):
        try:
            tok = json.load(open(TOKEN_FILE)).get('token', '')
        except Exception:
            pass
    if tok:
        s.cookies.set('merchant-token', tok, domain='pay.ldxp.cn')
        s.headers['merchant-token'] = tok
    return s


def refresh_acw_cookie(s: requests.Session) -> bool:
    """通过 Playwright 刷新 ACW 反爬 cookie"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True, args=['--no-sandbox'])
            c = b.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36')
            p = c.new_page()
            p.goto(BASE + '/merchant/my_parent/source_square', wait_until='load', timeout=30000)
            time.sleep(2)
            acw = next((x['value'] for x in c.cookies(BASE) if x['name'] == 'acw_sc__v2'), '')
            b.close()
            if acw:
                s.cookies.set('acw_sc__v2', acw, domain='pay.ldxp.cn')
                return True
    except Exception:
        pass
    return False


def login(s: requests.Session) -> bool:
    """登录链动平台，获取 merchant-token"""
    if not PASSWORD:
        return False
    for data in [
        {'username': USERNAME, 'password': PASSWORD},
        {'account': USERNAME, 'password': PASSWORD},
    ]:
        try:
            r = s.post(BASE + '/merchantApi/user/login', json=data, timeout=20)
            j = r.json()
            tok = (j.get('data') or {}).get('merchant_token') or (j.get('data') or {}).get('token') or j.get('token')
            if tok:
                json.dump({'token': tok, 'ts': time.time()}, open(TOKEN_FILE, 'w'))
                s.cookies.set('merchant-token', tok, domain='pay.ldxp.cn')
                s.headers['merchant-token'] = tok
                return True
        except Exception:
            pass
    return False


def api_post(s: requests.Session, path: str, payload: dict, retry: bool = True) -> dict:
    """API 请求，自动处理 ACW 挑战和登录过期"""
    r = s.post(BASE + path, json=payload, timeout=30)
    ct = r.headers.get('content-type', '')
    if 'text/html' in ct and 'arg1=' in r.text and retry:
        refresh_acw_cookie(s)
        login(s)
        return api_post(s, path, payload, False)
    if r.status_code in (401, 403) and retry:
        login(s)
        return api_post(s, path, payload, False)
    return r.json()


def fetch_all_goods(s: requests.Session, limit: int = 100, max_pages: int = 120) -> list[dict]:
    """拉取全量商品，返回 NormItem 列表"""
    out = []
    total = None
    fetched_at = time.time()
    for cur in range(1, max_pages + 1):
        payload = {'current': cur, 'pageSize': limit, 'goods_type': 'card', 'keywords': '', 'name': ''}
        try:
            j = api_post(s, '/merchantApi/MyParent/searchGoodsList', payload)
        except Exception:
            break
        data = j.get('data') or {}
        total = data.get('total') if isinstance(data, dict) else total
        # Extract raw items
        raw_items = data.get('list') if isinstance(data, dict) else []
        if not isinstance(raw_items, list):
            raw_items = []
        for x in raw_items:
            item = normalize_item(x, source='ldxp', fetched_at=fetched_at)
            if item:
                out.append(item)
        if not raw_items or (total and len(out) >= int(total)):
            break
    # Deduplicate by (source_id, title, supplier_id)
    seen = {}
    for it in out:
        key = (it.source_id, it.title, it.supplier_id)
        seen[key] = it
    return list(seen.values()), int(total or len(seen))


def fetch_merchants(s: requests.Session, limit: int = 100, max_pages: int = 50) -> list[dict]:
    """拉取商家列表"""
    rows = []
    total = None
    for cur in range(1, max_pages + 1):
        try:
            j = api_post(s, '/merchantApi/GoodsPool/list', {'current': cur, 'pageSize': limit, 'tags_id': 0})
        except Exception:
            break
        d = j.get('data') or {}
        arr = d.get('list') if isinstance(d, dict) else []
        total = d.get('total') if isinstance(d, dict) else total
        for m in arr or []:
            u = m.get('user') or {}
            rows.append({
                'title': (m.get('title') or '').strip(),
                'goods_count': int(m.get('goods_count') or 0),
                'status': m.get('status'),
                'shop_name': (u.get('nickname') or '').strip(),
                'agent_key': (u.get('agent_key') or '').strip(),
                'link': (u.get('link') or '').strip(),
            })
        if not arr or (total and len(rows) >= int(total)):
            break
    return rows, int(total or len(rows))


def fetch_shop_direct(shop_slug: str, max_pages: int = 30) -> tuple:
    """直接抓取指定店铺的商品（Playwright）。
    
    用于未开启"货源名片"的店铺 —— 通过 Playwright 访问店铺页面，
    捕获页面自动调用的 /shopApi/Shop/goodsList API，提取 token/visitorid 后翻页。
    
    Returns:
        (shop_info: dict | None, items: list[dict], error: str | None)
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, [], 'Playwright 未安装'
    
    # 店铺 API 字段名与货品池不同，需要映射
    def _adapt_shop_item(x: dict) -> dict:
        """将 shopApi 返回格式转为 normalize_item 期望的货品池格式"""
        ext = x.get('extend', {}) or {}
        user = x.get('user', {}) or {}
        link = user.get('link', '')
        # 从 user.link 提取 shop slug
        shop_slug_from_link = ''
        if '/shop/' in link:
            shop_slug_from_link = link.rsplit('/shop/', 1)[-1].split('?')[0]
        return {
            'id': x.get('goods_key') or x.get('id', ''),
            'name': x.get('name', ''),
            'title': x.get('name', ''),
            'description': x.get('description', ''),
            'price': x.get('price', 0),
            'market_price': x.get('market_price', 0),
            'stock_count': ext.get('stock_count', 0),
            'stock': ext.get('stock_count', 0),
            'inventory': ext.get('stock_count', 0),
            'goods_type': x.get('goods_type', 'card'),
            'link': x.get('link', ''),
            'user': user,
            'shop_id': shop_slug_from_link,
            'shop_name': user.get('nickname', ''),
            'category_name': (x.get('category') or {}).get('name', '') if isinstance(x.get('category'), dict) else '',
            'status': 1,  # 店铺页面的商品都是上架状态
        }
    
    shop_info = {}
    all_items = []
    fetched_at = time.time()
    
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True, args=['--no-sandbox'])
            ctx = b.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36')
            page = ctx.new_page()
            
            # Capture first goods request to get token + visitorid
            first_req = {}
            def capture_first(req):
                if '/shopApi/Shop/goodsList' in req.url and not first_req:
                    first_req['headers'] = dict(req.headers)
                    first_req['post_data'] = req.post_data
            
            # Capture responses
            info_data = {}
            goods_page1 = {}
            def handle_response(resp):
                if '/shopApi/Shop/info' in resp.url and resp.status == 200 and not info_data:
                    try:
                        info_data.update(resp.json())
                    except:
                        pass
                elif '/shopApi/Shop/goodsList' in resp.url and resp.status == 200 and not goods_page1:
                    try:
                        goods_page1.update(resp.json())
                    except:
                        pass
            
            page.on('request', capture_first)
            page.on('response', handle_response)
            
            page.goto(f'{BASE}/shop/{shop_slug}', wait_until='networkidle', timeout=30000)
            time.sleep(3)
            
            # Extract shop info
            si = info_data.get('data', {}) or {}
            shop_info = {
                'slug': shop_slug,
                'nickname': si.get('nickname', ''),
                'description': si.get('description', ''),
                'avatar': si.get('avatar', ''),
                'link': si.get('link', f'{BASE}/shop/{shop_slug}'),
            }
            
            # Process page 1 goods
            gd = goods_page1.get('data', {}) or {}
            items_page1 = gd.get('list', [])
            total = gd.get('total', len(items_page1))
            for x in items_page1:
                item = normalize_item(_adapt_shop_item(x), source='ldxp', fetched_at=fetched_at)
                if item:
                    all_items.append(item)
            
            # Extract token + visitorid + category_id for pagination
            post_data_raw = first_req.get('post_data', '{}')
            try:
                post_data = json.loads(post_data_raw)
            except:
                post_data = {}
            token = post_data.get('token', shop_slug)
            visitorid = first_req.get('headers', {}).get('visitorid', '')
            
            # Re-fetch page 1 with category_id=0 to get ALL goods (not just default category)
            # This gives us the correct total across all categories
            all_items = []  # reset — discard auto-fetched page 1
            result = page.evaluate("""
                async ([headers, body]) => {
                    const r = await fetch('/shopApi/Shop/goodsList', {
                        method: 'POST',
                        headers: headers,
                        body: JSON.stringify(body)
                    });
                    return await r.json();
                }
            """, [
                {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json, text/plain, */*',
                    'visitorid': visitorid,
                },
                {
                    'token': token,
                    'keywords': '',
                    'category_id': 0,
                    'goods_type': 'card',
                    'current': 1,
                    'pageSize': 100,
                }
            ])
            
            if result and result.get('code') == 1:
                pg_data = result.get('data', {}) or {}
                items_p1 = pg_data.get('list', [])
                total = pg_data.get('total', len(items_p1))
                for x in items_p1:
                    item = normalize_item(_adapt_shop_item(x), source='ldxp', fetched_at=fetched_at)
                    if item:
                        all_items.append(item)
            else:
                total = 0
            
            # Paginate remaining pages
            if total > len(all_items):
                total_pages = (total + 99) // 100
                for cur in range(2, min(total_pages + 1, max_pages + 1)):
                    result = page.evaluate("""
                        async ([headers, body]) => {
                            const r = await fetch('/shopApi/Shop/goodsList', {
                                method: 'POST',
                                headers: headers,
                                body: JSON.stringify(body)
                            });
                            return await r.json();
                        }
                    """, [
                        {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json, text/plain, */*',
                            'visitorid': visitorid,
                        },
                        {
                            'token': token,
                            'keywords': '',
                            'category_id': 0,
                            'goods_type': 'card',
                            'current': cur,
                            'pageSize': 100,
                        }
                    ])
                    
                    if not result or result.get('code') != 1:
                        break
                    pg_data = result.get('data', {}) or {}
                    pg_items = pg_data.get('list', [])
                    if not pg_items:
                        break
                    for x in pg_items:
                        item = normalize_item(_adapt_shop_item(x), source='ldxp', fetched_at=fetched_at)
                        if item:
                            all_items.append(item)
            
            b.close()
        
        # Deduplicate
        seen = {}
        for it in all_items:
            key = (it.source_id, it.title, it.supplier_id)
            seen[key] = it
        all_items = list(seen.values())
        
        return shop_info, all_items, None
        
    except Exception as e:
        return None, [], str(e)
