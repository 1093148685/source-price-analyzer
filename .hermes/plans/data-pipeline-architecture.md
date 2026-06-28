# Source Price Analyzer — Data Pipeline 架构升级方案

> **For Hermes:** 按 phase 逐步实施，每 phase 先 TDD 再实现。

**Goal:** 将现有单源关键词分类系统升级为多源数据管道：采集→标准化→分类→去重→质检→排序→输出。支持多供应商接入，数据清洗/去重/挖掘功能化系统化。

**Architecture:** Pipeline 模式，7 个独立阶段通过标准化 schema 串联，每阶段可独立测试、替换、扩展。Connector 层抽象数据源差异，Classifier 阶段结合规则引擎 + AI 模型，Deduplicator 用文本相似度 + 价格聚类做实体解析。

**Tech Stack:** Python (已有), scikit-learn (TF-IDF 去重), Levenshtein (模糊匹配), SQLite (全量数据持久化), 现有 FastAPI + React 前端

---

## Pipeline 总览

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ Connector│ → │Normalizer│ → │Classifier│ → │Dedup     │ → │Quality   │ → │ Ranker   │ → │Exporter  │
│ 多源采集  │   │ 标准化    │   │ 分类打标  │   │ 去重合并  │   │ 质检评分  │   │ 排序择优  │   │ API/缓存  │
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
     ↓               ↓               ↓               ↓               ↓               ↓               ↓
  RawItem        NormItem       ClassifiedItem   MergedItem      ScoredItem      RankedItem      Cached
  (raw dict)    (unified)      (type+subtype)  (dedup key)    (trust score)  (best price)    (old format)
```

---

## Phase 1: 核心 schema 定义 + Normalizer (数据标准化层)

### 目标
定义统一数据模型，将所有来源的原始数据转为标准格式。替换当前 `normalize()` 中的硬编码字段映射。

### Schema: `NormItem`
```python
@dataclass
class NormItem:
    # 唯一标识
    source_id: str          # 原始平台商品ID
    source: str             # 数据来源 (ldxp, api_xxx, csv_xxx)
    
    # 商品信息
    title: str
    description: str
    price: float            # 统一为 CNY
    currency: str = "CNY"
    stock: int = 0
    status: int = 1         # 1=在售, 0=下架
    
    # 商家信息
    supplier_id: str
    supplier_name: str
    supplier_url: str = ""
    
    # 原始分类
    category_raw: str = ""
    
    # 链接
    url: str = ""
    
    # 元数据
    raw_data: dict = None   # 保留原始数据用于调试
    fetched_at: float = 0   # 采集时间戳
```

### 文件
- 新增: `pipeline/__init__.py`
- 新增: `pipeline/schema.py` — NormItem 数据类 + 序列化
- 新增: `pipeline/normalizer.py` — 各数据源 field mapping 配置 + normalize 函数
- 新增: `pipeline/connectors/__init__.py`
- 新增: `pipeline/connectors/ldxp.py` — 链动连接器（从 app.py 迁移 login/fetch 逻辑）

### 关键: Field Mapping 配置化
```python
# pipeline/normalizer.py
SOURCE_MAPPINGS = {
    "ldxp": {
        "source_id": ("id", "goods_key", "goods_id", "link"),
        "title": ("name", "title", "goods_name"),
        "price": ("price", "agent_price3", "agent_price2", "agent_price1", "cost_price"),
        "supplier_id": ("shop.agent_key", "shop_id", "shop.id"),
        "supplier_name": ("shop.nickname", "shop_name", "shop.name"),
        ...
    },
    # 未来新增来源只需加配置
    "some_api": { ... }
}
```

### TODO
- [ ] Schema 定义 + 单元测试
- [ ] Normalizer 实现 + field_mapping 配置
- [ ] LDXP Connector 迁移（从 app.py 拆出 login/session/fetch_all_goods）
- [ ] 更新 app.py 使用新 pipeline 入口
- [ ] 缓存兼容：旧 cache_v2.json 可导入

---

## Phase 2: Classifier (分类引擎) — 规则 + AI 双通道

### 目标
替代当前 `classify_item()` + `PRODUCT_TYPES` + `RULES` 的硬编码方式。改为：规则引擎做粗筛 → AI 模型做细分类 + 交叉验证。新增产品类型只需加配置，不改代码。

### 架构
```
NormItem → [Product Detector] → ProductType
         → [Subtype Classifier] → SubType  
         → [AI Verifier] → trusted? + suggested_reclassification
```

### Product Detector (产品大类识别)
```python
# pipeline/classifier/product_detector.py
# 配置化产品定义，从 JSON/YAML 加载
PRODUCT_DEFINITIONS = [
    {
        "slug": "chatgpt",
        "name": "ChatGPT",
        "match": {"keywords": ["chatgpt", "gpt", "openai"], 
                  "exclude": ["codex", "接码", "api中转", "hotmail", "outlook", "邮箱"]},
        "priority": 10
    },
    ...
]
```

### Subtype Classifier (子类识别)
- 规则通道: 同现有逻辑，但配置化
- AI 通道: 对 `-other` 桶 + 低置信度商品做 AI 复核
- AI 缓存: `ai_classify.json` 持久化已分类结果

### 文件
- 新增: `pipeline/classifier/__init__.py`
- 新增: `pipeline/classifier/product_detector.py`
- 新增: `pipeline/classifier/subtype_classifier.py`
- 新增: `pipeline/classifier/ai_classifier.py` — AI 分类（迁移现有 ai_classify_item）
- 新增: `pipeline/classifier/product_definitions.yaml` — 产品定义配置

---

## Phase 3: Deduplicator (去重/实体解析)

### 目标
同一商品（如 "ChatGPT Plus 成品号"）被多个供应商售卖时，识别为同一实体。不合并数据，但打上 `entity_key` 标签，前端可以按 entity_key 聚合比价。

### 算法
```
Stage 1: 文本相似度 (TF-IDF + cosine)
  - 对所有同 ProductType 的商品标题计算 TF-IDF 向量
  - cosine similarity > 0.75 → 候选匹配对
  
Stage 2: 价格聚类验证
  - 候选对价格差异 < 30% → 确认匹配
  
Stage 3: 供应商去重
  - 同一 supplier 的同 entity_key 只保留最新
```

### 输出
每件商品新增 `entity_key` 字段（如 `chatgpt-plus-account__成品号`），前端可按此聚合。

### 文件
- 新增: `pipeline/deduplicator.py`
- 依赖: `scikit-learn` (TfidfVectorizer), `python-Levenshtein`

---

## Phase 4: Quality Scorer (质检评分)

### 目标
给每件商品打分（0-100），评估可信度。替代当前 `assess_quality()` 的简单布尔判断。

### 评分维度
| 维度 | 权重 | 规则 |
|------|------|------|
| 价格合理性 | 30% | 同类商品中位数 ±2σ 内满分，极端离群 0 分 |
| 描述完整度 | 15% | 有标题+描述+库存信息 |
| 供应商信誉 | 25% | 商品数量、历史价格稳定性、投诉率 |
| 数据新鲜度 | 10% | 最近 24h 内更新 |
| AI 复核 | 20% | AI 判定可信则满分 |

### 输出
`quality_score: 0-100`, `quality_flags: [str]`（如 "价格异常低", "描述缺失"）

### 文件
- 新增: `pipeline/quality.py`

---

## Phase 5: Ranker + Aggregator (排序择优)

### 目标
按 entity_key 聚合，输出每类商品的最佳供应商排名。

### 输出
```json
{
  "entity": "chatgpt-plus-account__成品号",
  "best_supplier": {"name": "卷子ai", "price": 12.5, "score": 92},
  "alternatives": [...],
  "price_range": {"min": 10, "max": 25, "median": 15},
  "supplier_count": 8
}
```

### 文件
- 新增: `pipeline/ranker.py`

---

## Phase 6: Exporter + API 适配

### 目标
Pipeline 输出适配现有 API 格式（`/api/summary`, `/api/product/{slug}`），前端无需改动。

### 文件
- 修改: `app.py` — 用 pipeline 替换 build_snapshot
- 新增: `pipeline/exporter.py` — 将 pipeline 输出转为现有 API 格式

---

## Phase 7: 数据持久化 + SQLite

### 目标
告别 JSON 缓存文件，改用 SQLite 做全量数据存储。支持：
- 价格历史追踪（同商品多次采集的价格变化）
- 供应商历史表现
- 增量更新（只拉变化商品）

### Schema
```sql
CREATE TABLE items (
    id TEXT PRIMARY KEY,
    source TEXT, source_id TEXT,
    title TEXT, description TEXT,
    price REAL, currency TEXT DEFAULT 'CNY',
    stock INTEGER, status INTEGER DEFAULT 1,
    supplier_id TEXT, supplier_name TEXT,
    category_raw TEXT, url TEXT,
    type_slug TEXT, subtype_slug TEXT,
    entity_key TEXT,
    quality_score REAL,
    created_at REAL, updated_at REAL
);

CREATE TABLE price_history (
    item_id TEXT, price REAL, recorded_at REAL,
    FOREIGN KEY(item_id) REFERENCES items(id)
);

CREATE TABLE suppliers (
    id TEXT PRIMARY KEY,
    name TEXT, url TEXT,
    total_items INTEGER,
    avg_quality_score REAL,
    first_seen REAL, last_seen REAL
);
```

### 文件
- 新增: `pipeline/storage.py` — SQLite CRUD
- 新增: `pipeline/migrations.py` — Schema 迁移

---

## 文件结构

```
/opt/data/apps/source-price-analyzer/
├── app.py                    # FastAPI (改用 pipeline)
├── admin.py                  # 管理后台
├── dns_manager.py            # DNS 管理
├── pipeline/
│   ├── __init__.py
│   ├── schema.py             # NormItem 等数据类
│   ├── normalizer.py         # 字段映射 + normalize
│   ├── classifier/
│   │   ├── __init__.py
│   │   ├── product_detector.py
│   │   ├── subtype_classifier.py
│   │   ├── ai_classifier.py
│   │   └── product_definitions.yaml
│   ├── deduplicator.py
│   ├── quality.py
│   ├── ranker.py
│   ├── exporter.py           # 输出格式转换
│   ├── storage.py            # SQLite 存储
│   ├── migrations.py
│   └── connectors/
│       ├── __init__.py
│       └── ldxp.py           # 链动小铺连接器
├── data/
│   ├── products.db           # SQLite 数据库 (新)
│   ├── product_definitions.yaml -> ../pipeline/classifier/
│   └── cache_v2.json         # 旧缓存 (逐步废弃)
├── frontend/                 # React (不改)
└── static/                   # Build 产物
```

---

## 实施优先级

1. **Phase 1 (Schema + Normalizer + LDXP Connector)** — 基础，不然后面没法做
2. **Phase 2 (Classifier)** — 替换现有分类逻辑
3. **Phase 6 (Exporter + API 适配)** — 让前端能用，保持向下兼容
4. **Phase 3 (Deduplicator)** — 核心价值：同商品比价
5. **Phase 4 (Quality Scorer)** — 数据可信度
6. **Phase 5 (Ranker)** — 最佳推荐
7. **Phase 7 (SQLite)** — 数据持久化，替换 JSON 缓存

---

## 向下兼容

- 旧 API 格式不变 (`/api/summary`, `/api/product/{slug}`)
- 旧缓存 `cache_v2.json` 可导入新系统
- 前端 React 不需要改（只要 exporter 输出格式匹配）
- admin.py 健康检测改为调用 pipeline

## 不做的事 (YAGNI)

- 实时 WebSocket 推送价格变化
- 用户系统/登录
- 支付集成
- 移动端 App
- 供应商 API 自动注册
