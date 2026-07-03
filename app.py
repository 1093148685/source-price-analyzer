import os,re,json,time,html,statistics,requests,subprocess
from typing import Any
from fastapi import FastAPI,Request,Form
from fastapi.responses import HTMLResponse,JSONResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment,FileSystemLoader,select_autoescape
APP_DIR=os.path.dirname(os.path.abspath(__file__))
DATA_DIR=os.path.join(APP_DIR,'data'); os.makedirs(DATA_DIR,exist_ok=True)
CACHE_FILE=os.path.join(DATA_DIR,'cache_v2.json')
TOKEN_FILE=os.path.join(DATA_DIR,'token.json')
CONFIG_FILE=os.path.join(DATA_DIR,'ai_config.json')
AI_REVIEW_FILE=os.path.join(DATA_DIR,'ai_reviews.json')
BASE='https://pay.ldxp.cn'
USERNAME=os.getenv('LDXP_USERNAME','hugojin')
PASSWORD=os.getenv('LDXP_PASSWORD','')
ESA_COOKIE=os.getenv('LDXP_ACW_SC_V2','6a4007d7730ae78566fffb44cbf834f097d9e889')
CACHE_TTL=int(os.getenv('SOURCE_PRICE_CACHE_TTL','900'))
PRODUCT_TYPES=[
 {'slug':'chatgpt','name':'ChatGPT','vendor':'OpenAI','emoji':'🤖','keywords':['ChatGPT','GPT','OpenAI'],'anti_keywords':['claude','grok','supergrok','gemini','netflix','奈飞','夸克','百度网盘','云盘','apple id','icloud','苹果id','苹果账号','itunes','codex','接码','api中转','api key','openai api','hotmail','outlook','微软邮箱','空邮箱','全新邮箱','paypal','cursor','gojek','notion'],'desc':'ChatGPT Plus、Pro、Free、Team 会员与账号（不含Codex/API/邮箱）','platforms':['账号','会员','代充']},
 {'slug':'codex-api','name':'Codex / API','vendor':'OpenAI','emoji':'🔑','keywords':['codex','openai api','openai key','openai token','api key','接码','api额度','api中转','api反代','codex接码','paypal接码','cursor接码','gojek接码','notion'],'anti_keywords':['chatgpt plus','gpt plus','chatgpt pro','gpt pro','claude','grok','netflix','奈飞','夸克','百度网盘','云盘','apple id','邮箱','hotmail','outlook'],'desc':'OpenAI Codex、API Key/Token、接码、中转反代额度','platforms':['API','Token','接码','代充']},
 {'slug':'microsoft-email','name':'微软邮箱','vendor':'Microsoft','emoji':'📧','keywords':['hotmail','outlook','微软邮箱','空邮箱','全新邮箱','邮箱换绑','邮箱交付'],'anti_keywords':['gmail','谷歌邮箱','google邮箱','apple id','icloud','chatgpt plus','gpt plus','claude pro','grok','netflix','奈飞','夸克','百度网盘','游戏','王者','吃鸡','pubg','原神'],'desc':'Hotmail、Outlook 微软邮箱账号（含换绑/空邮箱/白号）','platforms':['邮箱','账号']},
 {'slug':'claude','name':'Claude','vendor':'Anthropic','emoji':'🧠','keywords':['Claude'],'anti_keywords':['chatgpt','gpt plus','gpt pro','grok','gemini','netflix','奈飞','codex','接码','api中转','api key','openai api','hotmail','邮箱'],'desc':'Claude Pro、Max、Team、成品号与代充','platforms':['账号','会员','代充']},
 {'slug':'grok','name':'Grok','vendor':'xAI','emoji':'𝕏','keywords':['Grok','SuperGrok','grok'],'anti_keywords':['chatgpt','gpt plus','gpt pro','claude','gemini','netflix','奈飞','codex','接码','api','邮箱'],'desc':'Grok / SuperGrok 会员账号与代充','platforms':['账号','会员']},
 {'slug':'netflix','name':'Netflix / 奈飞','vendor':'Netflix','emoji':'🎬','keywords':['Netflix','奈飞'],'anti_keywords':['chatgpt','claude','grok','夸克','百度网盘','apple id','codex','接码','api','邮箱'],'desc':'奈飞账号、车位、独享会员','platforms':['账号','流媒体']},
 {'slug':'cloud-drive','name':'网盘 / 云盘','vendor':'多平台','emoji':'☁️','keywords':['网盘','夸克','百度网盘','云盘'],'anti_keywords':['chatgpt','claude','grok','netflix','奈飞','apple id','codex','接码','api','邮箱'],'desc':'百度网盘、夸克网盘、云盘会员与工具','platforms':['网盘','工具']},
 {'slug':'apple','name':'Apple ID / 苹果','vendor':'Apple','emoji':'🍎','keywords':['Apple ID','苹果','iCloud'],'anti_keywords':['chatgpt','claude','grok','netflix','奈飞','夸克','百度网盘','云盘','地铁','游戏','吃鸡','王者','pubg','原神','和平精英','codex','接码','api','邮箱'],'desc':'Apple ID、iCloud、苹果相关账号','platforms':['账号','订阅']},]
RULES={
 'chatgpt':[('chatgpt-plus-official','ChatGPT Plus 官方/正规充值',['plus','官方','正规','直充','充值','质保订阅'],['成品','日抛','试用','team','团队','go ',' go','business','bug','教程','gemini','key','notion','苹果','apple','礼品卡','free','免费','普号'],'Plus 官方渠道/正规代充，同类店铺比价'),('chatgpt-plus-account','ChatGPT Plus 成品号',['plus','成品号'],['充值','官方','正规','pro','team','团队','go ',' go','business','bug','教程','gemini','notion','苹果'],'Plus 成品号/账号货源'),('chatgpt-plus-temp','ChatGPT Plus 日抛/试用',['plus','日抛','试用'],['官方充值','正规充值','team','business','go ',' go','bug','教程','gemini','notion'],'Plus 日抛、试用开通、短期渠道'),('chatgpt-pro-official','ChatGPT Pro 官方/代充',['pro','充值'],['prompt','proxy','proton','team','go ',' go','bug','教程','gemini','notion'],'Pro 会员充值/代充'),('chatgpt-pro-account','ChatGPT Pro 成品号',['pro','成品','账号'],['prompt','proxy','proton','plus','team','go ',' go','bug','教程','gemini','notion'],'Pro 成品号/账号'),('chatgpt-free','ChatGPT Free / 免费号',['free','免费','普号','普通号'],['plus','pro','team','go ',' go','bug','教程','gemini','notion'],'免费/普号账号'),('chatgpt-go','ChatGPT Go',['go','8美元','8 美元'],['pro','team','bug','教程','gemini','notion'],'ChatGPT Go 订阅'),('chatgpt-team','ChatGPT Team',['team','团队','business'],['go ',' go','bug','教程','gemini','notion','苹果'],'Team 团队订阅')],
 'codex-api':[('codex-longterm','Codex 长效接码',['长效','长期','30天','60天','90天','31-90','28-30'],['短效','25min','一次性','试用'],'Codex 长效接码（30天+）'),('codex-shortterm','Codex 短效接码',['短效','一次性','25min','试用'],['长效','长期','30天','60天','90天'],'Codex 短效/一次性接码'),('codex-api-key','API Key / Token',['api','key','token','额度'],['中转','反代','接码'],'API Key、Token、额度充值'),('codex-proxy','API 中转/反代',['中转','反代'],['接码','账号','成品'],'API 中转/反代服务'),('codex-misc','其他接码/API服务',['paypal','cursor','gojek','notion','接码'],['chatgpt','gpt plus','gpt pro','claude','邮箱','hotmail','outlook'],'PayPal/Cursor/Gojek/Notion 等接码')],
 'microsoft-email':[('hotmail-account','Hotmail 邮箱',['hotmail'],['outlook','空邮箱','白号'],'Hotmail 邮箱账号'),('outlook-account','Outlook 邮箱',['outlook'],['hotmail','空邮箱'],'Outlook 邮箱账号'),('email-empty','空邮箱/白号',['空邮箱','白号','全新邮箱','全新微软'],['hotmail成品','outlook成品','gmail'],'未绑定/全新的微软邮箱'),('email-transfer','邮箱换绑/交付',['换绑','邮箱交付','转移','绑邮箱','绑定邮箱'],['gmail','谷歌邮箱'],'用于换绑GPT等账号的邮箱')],
 'claude':[('claude-pro','Claude Pro',['pro'],['prompt','max','5x','20x','team','团队','bug','教程','gemini','grok','notion'],'Claude Pro 会员'),('claude-max','Claude Max',['max','5x','20x'],['pro','team','bug','教程','gemini','grok','notion'],'Claude Max 会员'),('claude-team','Claude Team',['team','团队'],['pro','max','bug','教程','gemini','grok','notion'],'Claude Team 会员'),('claude-account','Claude 成品号/普通号',['成品','账号','普号','普通'],['pro','max','team','bug','教程','gemini','grok','notion'],'Claude 账号货源')],
 'grok':[('grok-super','Super Grok 会员',['super','会员'],['api','中转','token','bug','教程','gemini','claude','接码','反代','notion'],'Super Grok 会员'),('grok-account','Grok 账号',['账号','成品','普号'],['super','api','中转','token','bug','教程','gemini','claude','接码','反代','notion'],'Grok 账号')],
 'netflix':[('netflix-premium','Netflix 高级/4K',['4k','高级','独享'],[],'Netflix 高级独享/4K'),('netflix-account','Netflix 账号/车位',['账号','车位','奈飞','netflix'],[],'Netflix 账号或车位')],
 'cloud-drive':[('quark-drive','夸克网盘',['夸克'],[],'夸克网盘会员/工具'),('baidu-drive','百度网盘',['百度网盘','百度'],[],'百度网盘会员/工具'),('drive-tools','网盘工具',['助手','工具','转存','追更'],[],'网盘工具/助手')],
 'apple':[('apple-id','Apple ID 账号',['apple id','苹果id','苹果账号'],['游戏','地铁','吃鸡','王者','pubg','原神','教程'],'Apple ID 账号'),('icloud','iCloud / 苹果订阅',['icloud','订阅'],['游戏','地铁','吃鸡','王者','pubg','原神','教程'],'iCloud 或苹果订阅')]}
app=FastAPI(title='链动货源价格')
app.mount('/static',StaticFiles(directory=os.path.join(APP_DIR,'static')),name='static')
app.mount('/assets',StaticFiles(directory=os.path.join(APP_DIR,'static','assets')),name='assets')
jinja=Environment(loader=FileSystemLoader(os.path.join(APP_DIR,'templates')),autoescape=select_autoescape(['html']))
def money(v):
 try:return float(v or 0)
 except Exception:return 0.0
def clean(s):
 s=html.unescape(str(s or '')); s=re.sub(r'<[^>]+>',' ',s); s=re.sub(r'\s+',' ',s); return s.strip()
def hay(item): return (clean(item.get('title'))+' '+clean(item.get('desc'))+' '+clean(item.get('category'))).lower()
def stat(items):
 ps=sorted([money(x.get('price')) for x in items if 0<money(x.get('price'))<50000]); shops={str(x.get('shop_id') or x.get('shop_name') or '') for x in items}
 return {'count':len(items),'shops':len([s for s in shops if s]),'stock':sum(int(float(x.get('stock') or 0)) for x in items),'min':ps[0] if ps else 0,'max':ps[-1] if ps else 0,'avg':round(sum(ps)/len(ps),2) if ps else 0,'median':statistics.median(ps) if ps else 0}
def normalize(raw):
 rows=[]; data=raw.get('data',raw)
 if isinstance(data,dict):
  for k in ['list','data','rows','items']:
   if isinstance(data.get(k),list): data=data[k]; break
 if not isinstance(data,list): return []
 for x in data:
  shop=x.get('shop') or x.get('merchant') or x.get('user') or {}
  price=money(x.get('agent_price_limit') or x.get('price') or x.get('agent_price3') or x.get('agent_price2') or x.get('agent_price1') or x.get('cost_price') or x.get('sale_price') or x.get('selling_price'))
  cat=x.get('category') or {}
  # Extract shop_id from user.link if agent_key is missing
  shop_slug=''
  sl=shop.get('link') or ''
  import re as _re
  m=_re.search(r'/shop/([^/\s?#]+)', sl)
  if m: shop_slug=m.group(1)
  rows.append({'id':str(x.get('id') or x.get('goods_key') or x.get('goods_id') or x.get('goodsId') or x.get('link') or ''),'title':clean(x.get('name') or x.get('title') or x.get('goods_name')),'desc':clean(x.get('description') or x.get('desc') or x.get('subtitle'))[:420],'price':price,'stock':int(float(x.get('stock_count') or x.get('stock') or x.get('inventory') or 0)),'shop_name':clean(shop.get('nickname') or x.get('shop_name') or shop.get('name') or x.get('merchant_name')),'shop_id':str(shop.get('agent_key') or shop_slug or x.get('shop_id') or shop.get('id') or x.get('merchant_id') or ''),'category':clean(cat.get('name') if isinstance(cat,dict) else (x.get('category_name') or x.get('tag_name') or x.get('group_name'))),'link':clean(x.get('link')),'status':int(x.get('status') or 1),'raw':x})
 return [r for r in rows if r['title']]

def default_ai_config():
 return {'enabled':False,'base_url':'','model':'','api_key':'','temperature':0,'batch_size':20,'mode':'rules-first'}
def load_ai_config(mask=False):
 cfg=default_ai_config()
 if os.path.exists(CONFIG_FILE):
  try: cfg.update(json.load(open(CONFIG_FILE)))
  except Exception: pass
 if mask and cfg.get('api_key'):
  v=cfg['api_key']; cfg['api_key_masked']=v[:4]+'••••'+v[-4:] if len(v)>8 else '••••'; cfg['api_key']=''
 return cfg
def save_ai_config(data):
 cfg=load_ai_config(False); cfg.update(data)
 if not data.get('api_key') and cfg.get('api_key'): pass
 json.dump(cfg,open(CONFIG_FILE,'w'),ensure_ascii=False,indent=2)
 return cfg

def sku_key(item):
 text=hay(item)
 keys=[]
 if any(x in text for x in ['官方','正规','直充','充值','卡密','cdk','ios','菲区','美区','土区']): keys.append('官方充值/CDK')
 if any(x in text for x in ['成品号','账号','首登','带rt','非日抛']): keys.append('成品号')
 if any(x in text for x in ['日抛','试用','短期']): keys.append('短期/试用')
 if any(x in text for x in ['质保一个月','质保30','30天','一个月','月卡']): keys.append('月卡/30天')
 if any(x in text for x in ['无质保','不质保']): keys.append('无质保')
 if any(x in text for x in ['质保']): keys.append('有质保')
 return ' · '.join(keys[:3]) or '标准货源'

def attach_skus(product):
 groups={}
 for it in product.get('items',[]):
  k=sku_key(it); groups.setdefault(k,[]).append(it)
 skus=[]
 for k,items in groups.items():
  items=sorted(items,key=lambda x:(x.get('price',0)<=0,x.get('price',0)))
  st=stat(items); shops={str(x.get('shop_id') or x.get('shop_name')) for x in items}
  skus.append({'key':k,'name':k,'items':items,'stats':st,'shop_count':len([x for x in shops if x]),'best':items[0] if items else None})
 return sorted(skus,key=lambda x:(x['stats']['min']<=0,x['stats']['min']))

def item_key(product_slug,item):
 return product_slug+'|'+str(item.get('id') or '')+'|'+clean(item.get('title'))[:90]+'|'+str(item.get('price'))
def load_ai_reviews():
 if os.path.exists(AI_REVIEW_FILE):
  try: return json.load(open(AI_REVIEW_FILE))
  except Exception: return {}
 return {}
def save_ai_reviews(d):
 json.dump(d,open(AI_REVIEW_FILE,'w'),ensure_ascii=False,indent=2)
 try: os.chmod(AI_REVIEW_FILE,0o600)
 except Exception: pass

def ai_review_item(product_slug,product_name,item):
 cfg=load_ai_config(False)
 if not (cfg.get('enabled') and cfg.get('base_url') and cfg.get('api_key') and cfg.get('model')): return None
 prompt=("你是电商商品分类与比价质检器。判断商品是否属于目标产品，并输出严格JSON。"
  "字段: trusted(boolean), reason(string), normalized_sku(string), product_slug(string)。"
  "规则: 只判断是否属于目标产品，不因低于官方零售价直接否定；只有明显是API/token/教程/接码/账号或完全不相关才trusted=false。")
 user=json.dumps({'target_product_slug':product_slug,'target_product_name':product_name,'item':{'title':item.get('title'),'desc':item.get('desc'),'price':item.get('price'),'stock':item.get('stock'),'shop':item.get('shop_name'),'category':item.get('category')}},ensure_ascii=False)
 try:
  r=requests.post(cfg['base_url'].rstrip('/')+'/chat/completions',headers={'Authorization':'Bearer '+cfg['api_key'],'Content-Type':'application/json'},json={'model':cfg['model'],'messages':[{'role':'system','content':prompt},{'role':'user','content':user}],'temperature':float(cfg.get('temperature') or 0),'max_tokens':1500,'response_format':{'type':'json_object'}},timeout=35)
  if r.status_code!=200: return {'trusted':False,'reason':'AI接口错误:'+str(r.status_code),'ai_error':r.text[:160]}
  msg=r.json()['choices'][0]['message']; txt=(msg.get('content') or msg.get('reasoning_content') or '').strip()
  txt=re.sub(r'^```(?:json)?|```$','',txt.strip(),flags=re.I|re.M).strip()
  m=re.search(r'\{[\s\S]*\}',txt)
  if not m:
   return {'trusted':False,'reason':'AI未返回JSON','ai_error':txt[:160]}
  obj=json.loads(m.group(0))
  if 'trusted' not in obj:
   raw=json.dumps(obj,ensure_ascii=False)
   if 'true' in raw.lower() and 'false' not in raw.lower(): obj['trusted']=True
   elif 'false' in raw.lower(): obj['trusted']=False
  obj['trusted']=bool(obj.get('trusted'))
  obj['reason']=clean(obj.get('reason') or obj.get('理由') or obj.get(': true, ') or obj.get(': false, ') or '')[:180]
  obj['normalized_sku']=clean(obj.get('normalized_sku') or obj.get('sku') or obj.get('product') or '')[:80]
  obj['product_slug']=clean(obj.get('product_slug') or product_slug)[:80]
  return obj
 except Exception as e:
  return {'trusted':False,'reason':'AI调用失败:'+type(e).__name__,'ai_error':str(e)[:160]}

PRICE_FLOORS={
 'chatgpt-plus-official':30,'chatgpt-pro-official':150,'chatgpt-plus-account':1,'chatgpt-pro-account':1,
 'claude-pro':20,'claude-max':80,'grok-super':10,'netflix-premium':5
}
CONFLICT_WORDS={
 'chatgpt-plus-official':['codex','api','token','接码','教程','代理','交流群','部署','额度','日抛','试用','成品号'],
 'chatgpt-plus-account':['官方充值','正规充值','直充','codex','api','token','教程'],
 'chatgpt-pro-official':['plus','prompt','proxy','proton','codex','api','token','教程'],
 'openai-codex':['plus官方','plus 会员','pro会员','成品号'],
}
def assess_quality(product_slug,item):
 reasons=[]; price=money(item.get('price')); text=hay(item)
 # Status=0 = 商家已下架
 if item.get('status')==0:
  reasons.append('商家已下架(未上架)')
 floor=PRICE_FLOORS.get(product_slug)
 if floor and 0<price<floor: reasons.append(f'价格低于可信阈值¥{floor}')
 for w in CONFLICT_WORDS.get(product_slug,[]):
  if w.lower() in text: reasons.append('关键词冲突:'+w)
 if price<=0: reasons.append('无有效价格')
 if product_slug.endswith('official') and not any(w in text for w in ['官方','正规','直充','充值','卡密','cdk','ios','菲区','美区','土区','代充']): reasons.append('缺少充值/官方/CDK特征')
 rev=load_ai_reviews().get(item_key(product_slug,item))
 if rev:
  item['ai_review']=rev
  if rev.get('trusted') is True:
   reasons=[]
   item['ai_sku']=clean(rev.get('normalized_sku'))
  elif rev.get('trusted') is False:
   r=clean(rev.get('reason')) or 'AI判定不属于该具体产品'
   if r not in reasons: reasons.append('AI复核:'+r)
 return {'trusted':not reasons,'reasons':reasons,'label':'可信报价' if not reasons else '疑似混入'}

def finalize_product(b):
 for it in b.get('items',[]):
  q=assess_quality(b['slug'],it); it['trusted']=q['trusted']; it['quality_reasons']=q['reasons']; it['quality_label']=q['label']
 b['items']=sorted(b['items'],key=lambda x:(not x.get('trusted',True),x['price']<=0,x['price']))
 trusted=[x for x in b['items'] if x.get('trusted')]
 b['stats_all']=stat(b['items']); b['stats']=stat(trusted or b['items']); b['trusted_count']=len(trusted); b['suspicious_count']=len(b['items'])-len(trusted); b['skus']=attach_skus({'items':trusted or b['items']})
 # ── Price distribution histogram ──
 source_items=trusted or b['items']
 prices=sorted([x['price'] for x in source_items if x['price']>0])
 if len(prices)>=3:
  # Filter extreme outliers (IQR * 3)
  q1=prices[len(prices)//4]; q3=prices[3*len(prices)//4]; iqr=q3-q1
  upper=q3+3*iqr if iqr>0 else prices[-1]
  filtered=[p for p in prices if p<=upper]
  if len(filtered)>=3:
   min_p,max_p=filtered[0],filtered[-1]
   if max_p>min_p:
    nb=max(4,min(14,len(filtered)//4)); bw=(max_p-min_p)/nb
    dist=[]
    for i in range(nb):
     lo=min_p+i*bw; hi=min_p+(i+1)*bw
     if i==nb-1: cnt=sum(1 for p in filtered if lo-0.001<=p<=hi+0.001)
     else: cnt=sum(1 for p in filtered if lo-0.001<=p<hi)
     dist.append({'lo':round(lo,2),'hi':round(hi,2),'count':cnt,'pct':round(cnt/len(filtered)*100,1)})
    b['price_distribution']={'min':min_p,'max':max_p,'median':statistics.median(filtered),'buckets':dist,'total':len(filtered)}
 return b

def session():
 s=requests.Session(); s.cookies.set('acw_sc__v2',ESA_COOKIE,domain='pay.ldxp.cn')
 s.headers.update({'User-Agent':'Mozilla/5.0','Accept':'application/json, text/plain, */*','Referer':BASE+'/merchant/my_parent/source_square','Origin':BASE})
 tok=''
 if os.path.exists(TOKEN_FILE):
  try: tok=json.load(open(TOKEN_FILE)).get('token','')
  except Exception: pass
 if tok: s.cookies.set('merchant-token',tok,domain='pay.ldxp.cn'); s.headers['merchant-token']=tok
 return s

def refresh_acw_cookie(s):
 try:
  from playwright.sync_api import sync_playwright
  with sync_playwright() as pw:
   b=pw.chromium.launch(headless=True,args=['--no-sandbox'])
   c=b.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36')
   p=c.new_page(); p.goto(BASE+'/merchant/my_parent/source_square',wait_until='load',timeout=30000); time.sleep(2)
   acw=next((x['value'] for x in c.cookies(BASE) if x['name']=='acw_sc__v2'),'')
   b.close()
   if acw:
    s.cookies.set('acw_sc__v2',acw,domain='pay.ldxp.cn')
    return True
 except Exception: pass
 return False

def api_post(s,path,payload,retry=True):
 r=s.post(BASE+path,json=payload,timeout=30)
 ct=r.headers.get('content-type','')
 if 'text/html' in ct and 'arg1=' in r.text and retry:
  refresh_acw_cookie(s); login(s); return api_post(s,path,payload,False)
 if r.status_code in (401,403) and retry:
  login(s); return api_post(s,path,payload,False)
 return r.json()

def fetch_all_goods(s,limit=100,max_pages=120):
 out=[]; total=None
 for cur in range(1,max_pages+1):
  payload={'current':cur,'pageSize':limit,'goods_type':'card','keywords':'','name':''}
  try: j=api_post(s,'/merchantApi/MyParent/searchGoodsList',payload)
  except Exception: break
  data=j.get('data') or {}; arr=normalize(j); out.extend(arr)
  total=data.get('total') if isinstance(data,dict) else total
  if not arr or (total and len(out)>=int(total)): break
 seen={}
 for it in out: seen[(it.get('id'),it.get('title'),it.get('shop_id'))]=it
 return list(seen.values()), int(total or len(seen))

def fetch_merchants(s,limit=100,max_pages=50):
 rows=[]; total=None
 for cur in range(1,max_pages+1):
  try: j=api_post(s,'/merchantApi/GoodsPool/list',{'current':cur,'pageSize':limit,'tags_id':0})
  except Exception: break
  d=j.get('data') or {}; arr=d.get('list') if isinstance(d,dict) else []
  total=d.get('total') if isinstance(d,dict) else total
  for m in arr or []:
   u=m.get('user') or {}
   rows.append({'title':clean(m.get('title')),'goods_count':int(m.get('goods_count') or 0),'status':m.get('status'),'shop_name':clean(u.get('nickname')),'agent_key':clean(u.get('agent_key')),'link':clean(u.get('link'))})
  if not arr or (total and len(rows)>=int(total)): break
 return rows, int(total or len(rows))

def login(s):
 if not PASSWORD: return False
 for data in [{'username':USERNAME,'password':PASSWORD},{'account':USERNAME,'password':PASSWORD}]:
  try:
   r=s.post(BASE+'/merchantApi/user/login',json=data,timeout=20)
   j=r.json(); tok=(j.get('data') or {}).get('merchant_token') or (j.get('data') or {}).get('token') or j.get('token')
   if tok:
    json.dump({'token':tok,'ts':time.time()},open(TOKEN_FILE,'w')); s.cookies.set('merchant-token',tok,domain='pay.ldxp.cn'); s.headers['merchant-token']=tok; return True
  except Exception: pass
 return False

def fetch_keyword(s,kw):
 payload={'keyword':kw,'page':1,'limit':80,'pageSize':80}
 paths=['/merchantApi/MyParent/searchGoodsList','/merchantApi/GoodsPool/list']
 out=[]
 for p in paths:
  try:
   r=s.post(BASE+p,json=payload,timeout=25)
   if r.status_code in (401,403): login(s); r=s.post(BASE+p,json=payload,timeout=25)
   arr=normalize(r.json()); out.extend(arr)
  except Exception: pass
 seen={};
 for it in out:
  key=(it['id'],it['title'],it['shop_id']); seen[key]=it
 return list(seen.values())

def classify_item(type_slug,item):
 text=hay(item)
 for slug,name,inc,exc,desc in RULES.get(type_slug,[]):
  if any(x.lower() in text for x in inc) and not any(x.lower() in text for x in exc):
   return slug,name,desc,'rule'
 return type_slug+'-other','其他/待AI归类','未能明确归到具体套餐，后续交给AI模型细分','fallback'

AI_CLASSIFY_CACHE=os.path.join(DATA_DIR,'ai_classify.json')
def load_ai_classify():
 if os.path.exists(AI_CLASSIFY_CACHE):
  try: return json.load(open(AI_CLASSIFY_CACHE))
  except Exception: return {}
 return {}
def save_ai_classify(d):
 json.dump(d,open(AI_CLASSIFY_CACHE,'w'),ensure_ascii=False,indent=2)

def ai_classify_item(type_slug,type_name,item,available_slugs):
 """AI classifies an item into one of the available sub-type slugs, or rejects it (not-relevant)"""
 cfg=load_ai_config(False)
 if not (cfg.get('enabled') and cfg.get('base_url') and cfg.get('api_key') and cfg.get('model')): return None
 # Build sub-type descriptions
 slug_list=[]
 for tp in PRODUCT_TYPES:
  if tp['slug']==type_slug:
   slug_list=[{'slug':s,'name':n,'desc':d} for s,n,_,_,d in RULES.get(type_slug,[])]
   break
 if not slug_list:
  for tp in PRODUCT_TYPES:
   if tp['slug']==type_slug:
    slug_list=[{'slug':s,'name':n,'desc':d} for s,n,i,e,d in RULES.get(type_slug,[])]
    break
 prompt=(
  "你是电商商品智能归类器。一个商品被关键词匹配到了'{}'产品大类，但未能归入具体子类。\n"
  "请根据商品信息，判断它属于下面哪一个子类，或者完全不属于该产品大类(not-relevant)。\n"
  "可用子类: {}\n"
  "规则:\n"
  "1. 若商品确实属于{}的某个子类，输出 product_slug=该子类slug, trusted=true\n"
  "2. 若商品完全不相关(教程/API中转token/虚拟卡/接码/游戏账号/其他产品线)，输出 product_slug='not-relevant', trusted=false\n"
  "3. 价格极低(¥0-2)但标题含教程/接码/API/中转/额度/虚拟卡等词，trusted=false\n"
  "4. 仅输出JSON: {{\"trusted\":bool,\"reason\":\"简短理由\",\"product_slug\":\"子类slug或not-relevant\"}}"
 ).format(type_name,json.dumps(slug_list,ensure_ascii=False),type_name)
 user=json.dumps({'target_type':type_slug,'target_type_name':type_name,'available_slugs':[s['slug'] for s in slug_list],'item':{'title':item.get('title'),'desc':item.get('desc'),'price':item.get('price'),'stock':item.get('stock'),'shop':item.get('shop_name'),'category':item.get('category')}},ensure_ascii=False)
 try:
  r=requests.post(cfg['base_url'].rstrip('/')+'/chat/completions',headers={'Authorization':'Bearer '+cfg['api_key'],'Content-Type':'application/json'},json={'model':cfg['model'],'messages':[{'role':'system','content':prompt},{'role':'user','content':user}],'temperature':float(cfg.get('temperature') or 0),'max_tokens':800,'response_format':{'type':'json_object'}},timeout=30)
  if r.status_code!=200: return {'trusted':False,'reason':'API err '+str(r.status_code),'product_slug':type_slug+'-other','ai_error':r.text[:120]}
  msg=r.json()['choices'][0]['message']; txt=(msg.get('content') or msg.get('reasoning_content') or '').strip()
  txt=re.sub(r'^```(?:json)?|```$','',txt.strip(),flags=re.I|re.M).strip()
  m=re.search(r'\{[\s\S]*\}',txt)
  if not m: return {'trusted':True,'reason':'AI no JSON','product_slug':type_slug+'-other','ai_error':txt[:120]}
  obj=json.loads(m.group(0))
  obj['trusted']=bool(obj.get('trusted',True))
  obj['reason']=clean(obj.get('reason') or '')[:160]
  obj['product_slug']=clean(obj.get('product_slug') or type_slug+'-other')[:80]
  # Validate slug
  valid={s['slug'] for s in slug_list}|{type_slug+'-other','not-relevant'}
  if obj['product_slug'] not in valid: obj['product_slug']=type_slug+'-other'
  return obj
 except Exception as e:
  return {'trusted':True,'reason':'AI call fail:'+type(e).__name__,'product_slug':type_slug+'-other','ai_error':str(e)[:120]}

from pipeline.runner import run_pipeline as _run_pipeline
PIPELINE_CACHE_FILE = os.path.join(DATA_DIR, 'cache_pipeline.json')
DIRECT_SHOPS_FILE = os.path.join(DATA_DIR, 'direct_shops.json')

def load_direct_shop_items() -> dict:
    """加载通过店铺直抓收录的商品 {shop_slug: {shop_info, items: [...], ts}}"""
    try:
        if os.path.exists(DIRECT_SHOPS_FILE):
            return json.load(open(DIRECT_SHOPS_FILE))
    except Exception:
        pass
    return {}

def save_direct_shop_items(data: dict):
    """保存直抓收录数据"""
    json.dump(data, open(DIRECT_SHOPS_FILE, 'w'), ensure_ascii=False, indent=2)

def merge_direct_into_snapshot(snapshot: dict) -> dict:
    """将直抓收录的商品合并到 snapshot 中（all_items + types/products 分类结构）"""
    direct = load_direct_shop_items()
    if not direct:
        return snapshot
    
    from pipeline.classifier.product_detector import classify_product
    from pipeline.classifier.subtype_classifier import classify_subtype
    from pipeline.schema import NormItem
    
    all_items = list(snapshot.get('all_items', []))
    seen = {(str(it.get('id','')), it.get('title',''), str(it.get('shop_id',''))) for it in all_items}
    
    # Build type/product index for injection
    types_list = list(snapshot.get('types', []))
    products_list = list(snapshot.get('products', []))
    type_map = {t['slug']: t for t in types_list}
    # prod_map must point to the SAME objects as in type_map[t]['products']
    prod_map = {}
    prod_list_map = {}  # slug → index in products_list for syncing
    for t in types_list:
        for p in t.get('products', []):
            prod_map[p['slug']] = p
    # Also map top-level products for syncing later
    for idx, p in enumerate(products_list):
        prod_list_map[p['slug']] = idx
        if p['slug'] not in prod_map:
            prod_map[p['slug']] = p
    
    added = 0
    for slug, shop_data in direct.items():
        for it in shop_data.get('items', []):
            key = (str(it.get('id','')), it.get('title',''), str(it.get('shop_id','')))
            if key in seen:
                continue
            seen.add(key)
            
            # Classify
            ni = NormItem(
                source='ldxp', source_id=str(it.get('id','')),
                title=it.get('title',''), description=it.get('desc',''),
                price=float(it.get('price',0)), stock=int(it.get('stock',0) or 0),
                supplier_id=str(it.get('shop_id','')), supplier_name=it.get('shop_name',''),
                url=it.get('link',''), category_raw=it.get('category',''),
            )
            type_slug, type_name, conf = classify_product(ni)
            sub_slug, sub_name, method = classify_subtype(ni, type_slug)
            
            # Build legacy-format item
            ni.type_slug = type_slug
            ni.subtype_slug = sub_slug
            ni.quality_score = 100  # 直抓商品默认高置信度，确保 trusted=True
            ni.classify_method = 'direct-' + method  # 标记分类来源
            legacy_it = ni.to_legacy() if hasattr(ni, 'to_legacy') else {
                'id': ni.source_id, 'title': ni.title, 'desc': ni.description or '',
                'price': ni.price, 'stock': ni.stock,
                'shop_name': ni.supplier_name, 'shop_id': str(ni.supplier_id),
                'link': ni.url or '', 'category': ni.category_raw or '',
                'type_slug': type_slug, 'product_slug': sub_slug,
                'product_name': sub_name, 'classify_method': 'direct-' + method,
                'trusted': True, 'raw': {},
            }
            all_items.append(legacy_it)
            
            # Inject into type → product
            if type_slug not in type_map:
                # Create new type entry on the fly
                from pipeline.classifier.product_detector import PRODUCT_DEFINITIONS
                pd = next((p for p in PRODUCT_DEFINITIONS if p['slug'] == type_slug), None)
                new_type = {
                    'slug': type_slug, 'name': type_name,
                    'vendor': pd.get('vendor','') if pd else '',
                    'emoji': pd.get('emoji','') if pd else '',
                    'desc': pd.get('desc','') if pd else '',
                    'products': [], 'stats': None,
                }
                types_list.append(new_type)
                type_map[type_slug] = new_type
            
            t = type_map[type_slug]
            if sub_slug not in prod_map:
                new_prod = {
                    'slug': sub_slug, 'name': sub_name, 'desc': '',
                    'items': [], 'skus': [],
                    'stats_all': None, 'stats': None,
                    'trusted_count': 0, 'suspicious_count': 0,
                }
                t['products'].append(new_prod)
                products_list.append(new_prod)
                prod_map[sub_slug] = new_prod
            
            p = prod_map[sub_slug]
            p['items'].append(legacy_it)
            p['trusted_count'] += 1
            
            added += 1
    
    # Recompute stats for modified products and types
    # 遍历 types_list 中的产品（商品实际添加到的对象），而非旧 products_list
    for t in types_list:
        for p in t.get('products', []):
            items = p.get('items', [])
            if items:
                # stats_all = 所有商品；stats = 仅 trusted
                trusted_items = [i for i in items if i.get('trusted') != False]
                all_prices = sorted([float(i.get('price',0)) for i in items if float(i.get('price',0)) > 0])
                t_prices = sorted([float(i.get('price',0)) for i in trusted_items if float(i.get('price',0)) > 0])
                p['stats_all'] = {
                    'count': len(items),
                    'shops': len({i.get('shop_id') for i in items}),
                    'stock': sum(int(i.get('stock',0) or 0) for i in items),
                    'min': all_prices[0] if all_prices else 0,
                    'max': all_prices[-1] if all_prices else 0,
                    'avg': round(sum(all_prices)/len(all_prices),2) if all_prices else 0,
                }
                p['stats'] = {
                    'count': len(trusted_items),
                    'shops': len({i.get('shop_id') for i in trusted_items}),
                    'stock': sum(int(i.get('stock',0) or 0) for i in trusted_items),
                    'min': t_prices[0] if t_prices else 0,
                    'max': t_prices[-1] if t_prices else 0,
                    'avg': round(sum(t_prices)/len(t_prices),2) if t_prices else 0,
                }
    
    for t in types_list:
        all_prod_items = []
        for p in t.get('products', []):
            all_prod_items.extend(p.get('items', []))
        if all_prod_items:
            prices = sorted([float(i.get('price',0)) for i in all_prod_items if float(i.get('price',0)) > 0])
            t['stats'] = {
                'count': len(all_prod_items),
                'shops': len({i.get('shop_id') for i in all_prod_items}),
                'stock': sum(int(i.get('stock',0) or 0) for i in all_prod_items),
                'min': prices[0] if prices else 0,
                'max': prices[-1] if prices else 0,
                'avg': round(sum(prices)/len(prices),2) if prices else 0,
                'median': statistics.median(prices) if prices else 0,
            }
    
    snapshot['all_items'] = all_items
    snapshot['types'] = types_list
    # Sync products_list with type products (since types have the canonical copies)
    products_list = []
    for t in types_list:
        for p in t.get('products', []):
            products_list.append(p)
    snapshot['products'] = products_list
    snapshot['_direct_shop_items'] = added
    return snapshot

def snapshot_item_count(data: dict) -> int:
    """Count source items in a snapshot without counting direct-shop merge twice."""
    if not isinstance(data, dict):
        return 0
    for key in ('source_items', 'all_items'):
        val = data.get(key)
        if isinstance(val, list) and val:
            return len(val)
    total = 0
    for p in data.get('products') or []:
        items = p.get('items') if isinstance(p, dict) else None
        if isinstance(items, list):
            total += len(items)
    return total

def load_nonempty_snapshot(path: str):
    try:
        if os.path.exists(path):
            d = json.load(open(path))
            if snapshot_item_count(d) > 0:
                return d
    except Exception:
        pass
    return None

def save_snapshot_caches(data: dict):
    """Persist only non-empty base snapshots. Direct-shop data stays in direct_shops.json."""
    if snapshot_item_count(data) <= 0:
        return False
    json.dump(data, open(PIPELINE_CACHE_FILE, 'w'), ensure_ascii=False, indent=2)
    try:
        json.dump(data, open(CACHE_FILE, 'w'), ensure_ascii=False, indent=2)
    except Exception:
        pass
    return True

def build_snapshot(force=False):
    """使用 Pipeline 引擎: 采集→标准化→分类→分组；空抓取结果绝不覆盖旧缓存。"""
    if (not force) and os.path.exists(PIPELINE_CACHE_FILE):
        try:
            d = json.load(open(PIPELINE_CACHE_FILE))
            if time.time() - d.get('ts', 0) < CACHE_TTL and snapshot_item_count(d) > 0:
                return merge_direct_into_snapshot(d)
        except Exception:
            pass

    data = None
    try:
        result = _run_pipeline()
        candidate = result.to_legacy()
        if snapshot_item_count(candidate) > 0:
            data = candidate
            save_snapshot_caches(data)
    except Exception as e:
        data = None

    if data is None:
        # Upstream occasionally returns 0 items due to CDN/cookie issues. Keep the last good base snapshot.
        data = load_nonempty_snapshot(PIPELINE_CACHE_FILE) or load_nonempty_snapshot(CACHE_FILE)

    if data is None:
        data = load_legacy_cache()
        if data:
            data.setdefault('ai_config', {})['note'] = 'Pipeline 实时抓取为空，已回退旧货源缓存；店铺解析数据仍按增量合并。'
            save_snapshot_caches(data)

    if data is None:
        data = {'ts': time.time(), 'types': [], 'products': [], 'all_items': [], 'ai_config': {'mode': 'empty', 'note': '无可用货源缓存'}}
    return merge_direct_into_snapshot(data)

def load_legacy_cache():
 path=os.path.join(DATA_DIR,'cache.json')
 if not os.path.exists(path): return None
 old=json.load(open(path))
 types=[]; products=[]; all_items=[]
 for tp in PRODUCT_TYPES:
  g=next((x for x in old.get('groups',[]) if x.get('slug')==tp['slug'] or (tp['slug']=='chatgpt' and x.get('slug')=='chatgpt')),None)
  source=(g or {}).get('items') or (g or {}).get('best') or []
  buckets={}
  for x in source:
   it={'id':str(x.get('id') or ''),'title':clean(x.get('name') or x.get('title')),'desc':clean(x.get('summary') or x.get('desc'))[:420],'price':money(x.get('price')),'stock':int(float(x.get('stock') or 0)),'shop_name':clean(x.get('shop') or x.get('shop_name')),'shop_id':clean(x.get('contact') or x.get('shop_id') or x.get('shop_link')),'category':clean(x.get('category')),'raw':x}
   pslug,pname,pdesc,method=classify_item(tp['slug'],it)
   it['type_slug']=tp['slug']; it['product_slug']=pslug; it['product_name']=pname; it['classify_method']='legacy-'+method
   buckets.setdefault(pslug,{'slug':pslug,'name':pname,'desc':pdesc,'type':tp,'items':[]})['items'].append(it); all_items.append(it)
  prod=[]
  for b in buckets.values():
   b=finalize_product(b); prod.append(b); products.append(b)
  prod=sorted(prod,key=lambda x:(x['stats']['count']==0,x['stats']['min'] or 999999))
  types.append({**tp,'products':prod,'stats':stat(source)})
 return {'ts':time.time(),'types':types,'products':products,'all_items':all_items,'ai_config':{'mode':'legacy-cache+rules','note':'实时接口遇到CDN挑战时使用旧货源缓存；分类逻辑仍按AI-ready规则执行。'}}

def render(name,**ctx): return HTMLResponse(jinja.get_template(name).render(**ctx))

def tg_sync_status():
 path=os.path.join(DATA_DIR,'tg_sync_status.json')
 if os.path.exists(path):
  try: return json.load(open(path))
  except Exception: pass
 return {'ok':False,'message':'尚未同步到 TG 商品监控'}

def sync_to_tg_monitor():
 script=os.path.join(APP_DIR,'sync_tg_monitor.py')
 p=subprocess.run(['python3',script],cwd=APP_DIR,text=True,capture_output=True,timeout=360)
 if p.returncode!=0:
  return {'ok':False,'error':(p.stdout+'\n'+p.stderr)[-2000:]}
 try:
  return json.loads(p.stdout[p.stdout.find('{'):])
 except Exception:
  return {'ok':True,'raw':p.stdout[-2000:]}


def find_type(data,slug): return next((x for x in data['types'] if x['slug']==slug),None)
def find_product(data,slug): return next((x for x in data['products'] if x['slug']==slug),None)

@app.get('/settings',response_class=HTMLResponse)
def settings_page(request:Request):
 return render('settings.html',request=request,cfg=load_ai_config(True))

@app.post('/settings')
def settings_save(enabled:str=Form('off'),base_url:str=Form(''),model:str=Form(''),api_key:str=Form(''),temperature:float=Form(0),batch_size:int=Form(20),mode:str=Form('rules-first')):
 data={'enabled':enabled=='on','base_url':base_url.strip(),'model':model.strip(),'temperature':temperature,'batch_size':batch_size,'mode':mode}
 if api_key.strip(): data['api_key']=api_key.strip()
 save_ai_config(data)
 return RedirectResponse('/settings',status_code=303)

@app.get('/api/settings')
def api_settings(): return JSONResponse(load_ai_config(True))


@app.post('/api/ai/review/{slug}')
def api_ai_review(slug:str,limit:int=30):
 data=build_snapshot(False); p=find_product(data,slug)
 if not p: return JSONResponse({'ok':False,'error':'product not found'},status_code=404)
 cache=load_ai_reviews(); reviewed=[]
 candidates=[x for x in p.get('items',[]) if (not x.get('trusted',True)) or slug.endswith('other')]
 for it in candidates[:max(1,min(limit,80))]:
  k=item_key(slug,it)
  if k in cache: reviewed.append({'cached':True,'title':it.get('title'),'review':cache[k]}); continue
  rev=ai_review_item(slug,p.get('name'),it)
  if rev is None: return JSONResponse({'ok':False,'error':'AI not configured'},status_code=400)
  cache[k]=rev; reviewed.append({'cached':False,'title':it.get('title'),'review':rev})
 save_ai_reviews(cache)
 try: os.remove(CACHE_FILE)
 except Exception: pass
 return {'ok':True,'product':slug,'reviewed':len(reviewed),'items':reviewed[:20]}

@app.post('/api/ai/classify/{type_slug}')
def api_ai_classify(type_slug:str,limit:int=50):
 """Batch AI classify items in '-other' buckets for a product type"""
 data=build_snapshot(False)
 tp=find_type(data,type_slug)
 if not tp: return JSONResponse({'ok':False,'error':'type not found'},status_code=404)
 cache=load_ai_classify(); classified=[]; not_relevant=0
 # Gather all -other items across products
 candidates=[]
 for p in tp.get('products',[]):
  if p['slug'].endswith('-other'):
   for it in p.get('items',[]):
    k=item_key(type_slug,it)
    if k not in cache: candidates.append((p['slug'],it))
   for it in p.get('items',[]):
    k=item_key(type_slug,it)
    if k in cache: classified.append({'cached':True,'title':it.get('title'),'result':cache[k]})
 # Also include suspicious items
 for p in tp.get('products',[]):
  for it in p.get('items',[]):
   if not it.get('trusted',True):
    k=item_key(type_slug,it)
    if k not in cache and (p['slug'],it) not in [(s,i) for s,i in candidates]:
     candidates.append((p['slug'],it))
 # AI classify
 for pslug,it in candidates[:max(1,min(limit,100))]:
  k=item_key(type_slug,it)
  res=ai_classify_item(type_slug,tp['name'],it,[])
  if res is None: return JSONResponse({'ok':False,'error':'AI not configured'},status_code=400)
  res['_original_slug']=pslug
  cache[k]=res; classified.append({'cached':False,'title':it.get('title'),'result':res})
  if res.get('product_slug')=='not-relevant': not_relevant+=1
 save_ai_classify(cache)
 # Invalidate cache so next build picks up changes
 try: os.remove(CACHE_FILE)
 except Exception: pass
 return {'ok':True,'type':type_slug,'classified':len(classified),'not_relevant':not_relevant,'items':classified[-20:]}

@app.get('/api/ai/test')
def api_ai_test():
 cfg=load_ai_config(False)
 if not cfg.get('api_key'): return {'ok':False,'error':'missing api key'}
 sample={'title':'ChatGPT Plus 官方充值1个月','desc':'正规代充','price':120,'stock':1,'shop_name':'测试','category':'AI'}
 rev=ai_review_item('chatgpt-plus-official','ChatGPT Plus 官方/正规充值',sample)
 return {'ok':bool(rev and not rev.get('ai_error')),'model':cfg.get('model'),'review':rev}

@app.get('/refresh')
def refresh():
 build_snapshot(True); sync_to_tg_monitor(); return RedirectResponse('/products')

@app.get('/sync-tg')
def sync_tg_page():
 sync_to_tg_monitor(); return RedirectResponse('/')

@app.post('/api/tg-sync')
def api_tg_sync(): return JSONResponse(sync_to_tg_monitor())

@app.get('/api/tg-sync/status')
def api_tg_sync_status(): return JSONResponse(tg_sync_status())

@app.get('/api/data')
def api_data(force:int=0): return JSONResponse(build_snapshot(bool(force)))

@app.get('/api/summary')
def api_summary():
    """Lightweight endpoint - only types + products metadata, no items arrays (for fast SPA loading)"""
    data = build_snapshot(False)
    types = []
    for t in data.get('types', []):
        tc = {k: v for k, v in t.items() if k != 'products'}
        tc['products'] = []
        for p in t.get('products', []):
            pc = {k: v for k, v in p.items() if k not in ('items', 'skus')}
            tc['products'].append(pc)
        types.append(tc)
    # Top-level products metadata (no items/skus)
    products_meta = []
    for p in data.get('products', []):
        pc = {k: v for k, v in p.items() if k not in ('items', 'skus')}
        products_meta.append(pc)
    light = {
        'ts': data.get('ts'),
        'types': types,
        'products': products_meta,
        'ai_config': data.get('ai_config', {}),
        'source': data.get('source', {}),
    }
    return JSONResponse(light)
@app.get('/api/product/{slug}')
def api_product(slug:str):
    data=build_snapshot(False); return JSONResponse(find_product(data,slug) or {})

# ─────────── Admin API ───────────
from admin import (
    run_health_check, load_health_history, get_schedule_status,
    update_health_schedule, start_health_scheduler,
    admin_login, admin_setup, admin_logout, verify_admin_token,
    get_health_progress,
)

# Initialize scheduler on startup
@app.on_event('startup')
def startup_admin_scheduler():
    start_health_scheduler()

def _require_admin(request: Request):
    """Check admin token from header or cookie."""
    token = request.headers.get('X-Admin-Token') or request.cookies.get('admin_token')
    if not token or not verify_admin_token(token):
        return JSONResponse({'ok': False, 'error': '未授权'}, status_code=401)
    return None

@app.post('/api/admin/login')
def api_admin_login(password: str = Form('')):
    token = admin_login(password)
    if token:
        return JSONResponse({'ok': True, 'token': token})
    return JSONResponse({'ok': False, 'error': '密码错误'}, status_code=401)

@app.post('/api/admin/setup')
def api_admin_setup(password: str = Form('')):
    """Initial admin password setup (only works if no password set)."""
    from admin import load_admin_config
    cfg = load_admin_config()
    if cfg.get('password_hash'):
        return JSONResponse({'ok': False, 'error': '已设置过密码，请用 /api/admin/login'}, status_code=400)
    if not password or len(password) < 4:
        return JSONResponse({'ok': False, 'error': '密码至少4位'}, status_code=400)
    token = admin_setup(password)
    return JSONResponse({'ok': True, 'token': token})

@app.post('/api/admin/logout')
def api_admin_logout(request: Request):
    admin_logout()
    return JSONResponse({'ok': True})

@app.get('/api/admin/check-auth')
def api_admin_check_auth(request: Request):
    err = _require_admin(request)
    if err: return err
    return JSONResponse({'ok': True})

@app.post('/api/admin/health/run')
def api_admin_health_run(request: Request):
    err = _require_admin(request)
    if err: return err
    try:
        report = run_health_check()
        return JSONResponse({'ok': True, 'report': report})
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)

@app.get('/api/admin/health/progress')
def api_admin_health_progress(request: Request):
    err = _require_admin(request)
    if err: return err
    return JSONResponse({'ok': True, 'progress': get_health_progress()})

@app.get('/api/admin/health/status')
def api_admin_health_status(request: Request):
    err = _require_admin(request)
    if err: return err
    history = load_health_history()
    latest = history[-1] if history else None
    schedule = get_schedule_status()
    return JSONResponse({
        'ok': True,
        'latest': latest,
        'history': [{'ts': h['ts'], 'datetime': h['datetime'], 'summary': h['summary']} for h in history[-10:]],
        'schedule': schedule,
    })

@app.post('/api/admin/health/schedule')
def api_admin_health_schedule(request: Request, enabled: str = Form('false'), cron: str = Form('0 19 * * *'), timezone: str = Form('Asia/Shanghai')):
    err = _require_admin(request)
    if err: return err
    ok = update_health_schedule(enabled == 'true', cron, timezone)
    return JSONResponse({'ok': ok, 'schedule': get_schedule_status()})

@app.get('/api/admin/health/history')
def api_admin_health_history(request: Request, limit: int = 10):
    err = _require_admin(request)
    if err: return err
    history = load_health_history()
    return JSONResponse({
        'ok': True,
        'history': [{'ts': h['ts'], 'datetime': h['datetime'], 'summary': h['summary']} for h in history[-limit:]],
    })

# ─────────── NicNames DNS 管理 API ───────────
from dns_manager import (
    NicNamesDNS, save_credentials, load_credentials, start_nicnames_background_services, stop_nicnames_background_services,
    HAS_PLAYWRIGHT,
)

@app.get('/api/dns/status')
def api_dns_status():
    """DNS 模块状态检查"""
    creds = load_credentials()
    configured = bool(creds and creds.get('email'))
    has_playwright = HAS_PLAYWRIGHT
    return JSONResponse({
        'configured': configured,
        'email': (creds.get('email','')[:2]+'***@'+creds.get('email','').split('@')[-1]) if configured else '',
        'playwright': has_playwright,
    })

@app.get('/api/dns/config')
def api_dns_config_get():
    creds = load_credentials()
    if not creds:
        return JSONResponse({'configured': False})
    return JSONResponse({
        'configured': True,
        'email': creds.get('email','')[:2]+'***@'+creds.get('email','').split('@')[-1] if creds.get('email') else '',
    })

@app.post('/api/dns/config')
def api_dns_config_post(email: str = Form(''), password: str = Form('')):
    if not email or not password:
        return JSONResponse({'ok': False, 'error': 'email 和 password 必填'}, status_code=400)
    save_credentials(email, password)
    return JSONResponse({'ok': True, 'message': '凭据已保存'})

def _get_dns_manager():
    """Get NicNamesDNS instance from saved credentials."""
    creds = load_credentials()
    if not creds:
        return None, JSONResponse({'ok': False, 'error': '未配置 NicNames 凭据，请先 POST /api/dns/config'}, status_code=400)
    return NicNamesDNS(email=creds['email'], password=creds['password']), None

@app.get('/api/dns/domains')
def api_dns_domains():
    mgr, err = _get_dns_manager()
    if err: return err
    try:
        domains = mgr.get_domains()
        return JSONResponse({'ok': True, 'domains': domains})
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)

@app.get('/api/dns/records/{domain}')
def api_dns_records(domain: str):
    mgr, err = _get_dns_manager()
    if err: return err
    try:
        records = mgr.get_dns_records(domain)
        return JSONResponse({'ok': True, 'domain': domain, 'records': records})
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)

@app.post('/api/dns/record')
def api_dns_record_add(domain: str = Form(...), name: str = Form('@'), record_type: str = Form('A'), data: str = Form(...), ttl: int = Form(14400)):
    mgr, err = _get_dns_manager()
    if err: return err
    try:
        ok = mgr.add_dns_record(domain, name, record_type, data, ttl)
        return JSONResponse({'ok': ok, 'message': '记录已添加' if ok else '添加失败'})
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)

@app.delete('/api/dns/record')
def api_dns_record_delete(domain: str = Form(...), domain_id: str = Form(''), name: str = Form(...), record_type: str = Form('A'), data: str = Form(...)):
    mgr, err = _get_dns_manager()
    if err: return err
    try:
        # Resolve domain_id if not provided
        if not domain_id:
            domain_id = mgr.resolve_domain_id(domain)
        if not domain_id:
            return JSONResponse({'ok': False, 'error': f'未找到域名: {domain}'}, status_code=404)
        ok = mgr.delete_dns_record(domain_id, name, record_type, data)
        return JSONResponse({'ok': ok, 'message': '记录已删除' if ok else '删除失败'})
    except Exception as e:
        return JSONResponse({'ok': False, 'error': str(e)}, status_code=500)

# ── Shop Analyzer ──
@app.post('/api/analyze-shop')
async def api_analyze_shop(request: Request):
    """解析店铺：输入 shop URL(s)，自动拉取商品并分类"""
    import re as _re
    body = {}
    try:
        body = await request.json()
    except:
        pass
    
    urls = body.get('urls', []) or body.get('url', [])
    if isinstance(urls, str):
        urls = [urls]
    if not urls:
        return JSONResponse({'ok': False, 'error': '请提供店铺URL'}, status_code=400)
    
    # Extract shop slugs
    slugs = []
    for u in urls:
        m = _re.search(r'/shop/([^/\s?#]+)', str(u))
        if m:
            slugs.append(m.group(1))
    if not slugs:
        return JSONResponse({'ok': False, 'error': '未识别到店铺slug'}, status_code=400)
    
    # Load all goods (use cache or fresh)
    data = build_snapshot(False)
    all_items = data.get('all_items', [])
    
    # Filter and classify
    from pipeline.classifier.product_detector import classify_product, detect_product
    from pipeline.classifier.subtype_classifier import classify_subtype
    
    results = {}
    _direct_slugs = []
    _direct_full_items = {}  # slug -> full shop_items list for saving
    for slug in slugs:
        _shop_info = None
        _from_direct = False
        shop_items = [it for it in all_items if str(it.get('shop_id','')) == slug]
        if not shop_items:
            # Fallback: 直接抓取店铺页面（未开启货源名片的店铺）
            try:
                from pipeline.connectors.ldxp import fetch_shop_direct
                import asyncio
                loop = asyncio.get_event_loop()
                shop_info, norm_items, err = await loop.run_in_executor(None, fetch_shop_direct, slug)
                if err:
                    results[slug] = {'found': False, 'items': [], 'categories': {}, 'hint': f'直接抓取失败: {err}'}
                    continue
                if not norm_items:
                    results[slug] = {'found': False, 'items': [], 'categories': {}, 'hint': '店铺不存在或无商品'}
                    continue
                # Convert NormItem list to dict format
                shop_items = []
                for ni in norm_items:
                    shop_items.append({
                        'id': ni.source_id,
                        'title': ni.title,
                        'desc': ni.description or '',
                        'price': ni.price,
                        'stock': ni.stock,
                        'shop_name': ni.supplier_name,
                        'shop_id': str(ni.supplier_id),
                        'link': ni.url or '',
                        'category': ni.category_raw or '',
                        'trusted': True,
                        'raw': {},
                    })
                # Store shop info for response
                _shop_info = shop_info
                _from_direct = True
                _direct_full_items[slug] = list(shop_items)  # save copy for persistence
            except Exception as e:
                results[slug] = {'found': False, 'items': [], 'categories': {}, 'hint': f'直接抓取异常: {str(e)}'}
                continue
        if not shop_items:
            results[slug] = {'found': False, 'items': [], 'categories': {}, 'hint': '该店铺商品未出现在货品池中，尝试直接抓取也失败'}
            continue
        
        # Classify each item
        categorized = {}
        for it in shop_items:
            # Build a minimal NormItem
            from pipeline.schema import NormItem
            ni = NormItem(
                source='ldxp', source_id=str(it.get('id','')),
                title=it.get('title',''), description=it.get('desc',''),
                price=float(it.get('price',0)), stock=int(it.get('stock',0) or 0),
                supplier_id=str(it.get('shop_id','')), supplier_name=it.get('shop_name',''),
                url=it.get('link',''), category_raw=it.get('category',''),
            )
            type_slug, type_name, conf = classify_product(ni)
            sub_slug, sub_name, method = classify_subtype(ni, type_slug)
            
            key = f"{type_slug}|{sub_slug}"
            if key not in categorized:
                categorized[key] = {
                    'type_slug': type_slug, 'type_name': type_name,
                    'sub_slug': sub_slug, 'sub_name': sub_name,
                    'confidence': round(conf, 2), 'items': [],
                }
            categorized[key]['items'].append({
                'id': it.get('id'), 'title': it.get('title','')[:100],
                'price': it.get('price'), 'stock': it.get('stock',0),
                'link': it.get('link',''), 'trusted': it.get('trusted', True),
            })
        
        result_entry = {
            'found': True,
            'total': len(shop_items),
            'categories': sorted(categorized.values(), key=lambda x: -len(x['items'])),
        }
        if _shop_info:
            result_entry['shop_info'] = _shop_info
        if _from_direct:
            result_entry['indexed'] = True
            _direct_slugs.append(slug)
        results[slug] = result_entry
    
    # 自动收录：将直抓商品保存到持久化存储
    indexed_count = 0
    if _direct_slugs:
        direct = load_direct_shop_items()
        for slug in _direct_slugs:
            r = results[slug]
            full_items = _direct_full_items.get(slug, [])
            direct[slug] = {
                'shop_info': r.get('shop_info', {}),
                'items': full_items,
                'ts': time.time(),
            }
            indexed_count += len(full_items)
        save_direct_shop_items(direct)
    
    resp = {'ok': True, 'results': results, 'slugs': slugs}
    if indexed_count > 0:
        resp['indexed'] = indexed_count
        resp['message'] = f'已收录 {indexed_count} 件商品到站点分类中'
    return JSONResponse(resp)

# ── React SPA (built by Vite into static/) ──
REACT_INDEX = os.path.join(APP_DIR, 'static', 'index.html')
SPA_HTML = open(REACT_INDEX).read() if os.path.exists(REACT_INDEX) else '<html><body><h1>Frontend not built. Run: cd frontend && npm run build</h1></body></html>'

@app.get('/{full_path:path}', response_class=HTMLResponse)
async def spa_fallback(full_path: str):
    if full_path.startswith(('api/', 'static/', 'assets/')):
        from fastapi.responses import JSONResponse
        return JSONResponse({'error': 'not found'}, status_code=404)
    return HTMLResponse(SPA_HTML)

if __name__=='__main__':
 import uvicorn
 uvicorn.run(app,host=os.getenv('HOST','0.0.0.0'),port=int(os.getenv('PORT','8123')))
