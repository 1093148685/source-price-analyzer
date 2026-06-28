// API types
export interface ProductType {
  slug: string; name: string; vendor: string; emoji: string;
  platforms: string[];
  products: Product[];
  stats: Stats;
  agg?: AggStats;
}

export interface Product {
  slug: string; name: string; desc: string;
  type?: { slug: string; name: string; vendor: string };
  items: Item[];
  stats: Stats;
  trusted_count: number;
  suspicious_count: number;
  price_distribution?: PriceDist;
}

export interface Item {
  id: string; title: string; desc: string;
  price: number; stock: number;
  shop_name: string; shop_id: string;
  category: string; link: string;
  status?: number;
  trusted?: boolean;
  quality_reasons?: string[];
  quality_label?: string;
  type_slug: string; product_slug: string; product_name: string;
  raw?: any;
}

export interface Stats {
  count: number; shops: number; stock: number;
  min: number; max: number; avg: number; median: number;
}

export interface PriceDist {
  min: number; max: number; median: number; total: number;
  buckets: { lo: number; hi: number; count: number; pct: number }[];
  _maxCount?: number;
}

export interface ShopRow {
  shop_id: string; shop_name: string; shop_link: string;
  title: string; price: number; stock: number; count: number;
  sku_key: string;
}

export interface AppData {
  types: ProductType[];
  products: Product[];
  source: { ai_rejected: number; ai_reclassified: number; total_goods_api: number };
}

let cachedData: AppData | null = null;

export async function fetchData(force = 0): Promise<AppData> {
  if (cachedData && !force) return cachedData;
  const r = await fetch(`/api/summary?force=${force}`);
  cachedData = await r.json() as AppData;
  return cachedData!;
}

export function fmtPrice(v: number): string {
  if (v <= 0) return '¥0';
  return v >= 1 ? `¥${Math.floor(v)}` : `¥${v.toFixed(2)}`;
}

const NOISE_SLUGS = new Set([
  'chatgpt-free','chatgpt-plus-temp','openai-codex','chatgpt-other','chatgpt-team',
  'claude-account','claude-team','grok-account','drive-tools','apple-id'
]);

export function aggregateType(t: ProductType): AggStats {
  let totalItems = 0, totalStock = 0, minPrice = Infinity, productCount = 0;
  let maxShops = 0;
  for (const p of t.products || []) {
    productCount++;
    const s = p.stats;
    totalItems += s.count || 0;
    totalStock += s.stock || 0;
    if (s.shops > maxShops) maxShops = s.shops;
    if (!NOISE_SLUGS.has(p.slug) && (s.min || Infinity) < minPrice) minPrice = s.min;
  }
  if (minPrice === Infinity) {
    for (const p of t.products || []) {
      if (((p.stats || {}).min || Infinity) < minPrice) minPrice = p.stats.min;
    }
  }
  return { shopCount: maxShops, productCount, totalItems, totalStock, minPrice };
}

export interface AggStats {
  shopCount: number; productCount: number; totalItems: number; totalStock: number; minPrice: number;
}
