import { useEffect, useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { fetchData } from '../api';
import type { Product, ShopRow, PriceDist } from '../api';
import { getBigLogo } from '../logos';

function buildSkuKey(text: string): string {
  const keys: string[] = [];
  if (/官方|正规|直充|充值|卡密|cdk/.test(text)) keys.push('官方直充');
  if (/成品号|账号|首登/.test(text)) keys.push('成品号');
  if (/日抛|试用|短期/.test(text)) keys.push('短期');
  return keys.slice(0, 2).join(' · ') || '标准货源';
}

function buildShopRows(items: { shop_id: string; shop_name: string; title: string; price: number; stock: number; raw?: any }[]): ShopRow[] {
  const shops: Record<string, { name: string; items: typeof items }> = {};
  for (const it of items) {
    const key = it.shop_id || it.shop_name || 'unknown';
    if (!shops[key]) shops[key] = { name: it.shop_name || '未知', items: [] };
    shops[key].items.push(it);
  }
  const rows: ShopRow[] = [];
  for (const [k, v] of Object.entries(shops)) {
    const best = v.items.sort((a, b) => a.price - b.price)[0];
    const text = (best.title + (best.raw?.desc || '') + (best.raw?.category || '')).toLowerCase();
    rows.push({
      shop_id: k,
      shop_name: v.name,
      shop_link: (best as any).link || best.raw?.link || best.raw?.user?.link || `https://pay.ldxp.cn/shop/${k}`,
      title: best.title,
      price: best.price,
      stock: v.items.reduce((s, x) => s + (x.stock || 0), 0),
      count: v.items.length,
      sku_key: buildSkuKey(text),
    });
  }
  return rows.sort((a, b) => a.price - b.price);
}

function PriceChart({ dist }: { dist: PriceDist }) {
  const maxCount = Math.max(...dist.buckets.map(b => b.count), 1);
  return (
    <div className="price-chart-sidebar">
      <h4>价格分布</h4>
      <div className="chart-stats">
        <div className="chart-stat">
          <span className="chart-stat-label">最低</span>
          <span className="chart-stat-value">¥{dist.min?.toFixed(0)}</span>
        </div>
        <div className="chart-stat">
          <span className="chart-stat-label">中位</span>
          <span className="chart-stat-value">¥{dist.median?.toFixed(0)}</span>
        </div>
        <div className="chart-stat">
          <span className="chart-stat-label">最高</span>
          <span className="chart-stat-value">¥{dist.max?.toFixed(0)}</span>
        </div>
      </div>
      <div className="bar-group">
        {dist.buckets.map((b, i) => (
          <div key={i} className="bar-col">
            <div className="bar-count">{b.count}</div>
            <div
              className="bar"
              style={{ height: Math.max(3, 100 * (b.count / maxCount)) }}
              title={`¥${b.lo}~¥${b.hi}: ${b.count}个 (${b.pct}%)`}
            />
            <div className="bar-label">¥{b.lo.toFixed(0)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function PriceHighlight({ price, shopName, pctSaved }: { price: number; shopName: string; pctSaved: number }) {
  return (
    <div className="price-highlight">
      <p className="ph-label">✦ 最低价格</p>
      <div className="ph-price">¥{price.toFixed(2)}</div>
      <div className="ph-shop">{shopName}</div>
      {pctSaved > 0 && (
        <div className="ph-saved">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="22 17 13.5 8.5 8.5 13.5 2 7" /><polyline points="16 17 22 17 22 11" />
          </svg>
          比最高价省 {pctSaved}%
        </div>
      )}
    </div>
  );
}

export default function ComparePage() {
  const { slug } = useParams<{ slug: string }>();
  const [loading, setLoading] = useState(true);
  const [product, setProduct] = useState<Product | null>(null);
  const [allRows, setAllRows] = useState<ShopRow[]>([]);
  const [sortBy, setSortBy] = useState<'price' | 'stock' | 'shop'>('price');
  const [inStock, setInStock] = useState(true);
  const [activeSku, setActiveSku] = useState('');
  const [showAll, setShowAll] = useState(false);

  // Load data: metadata from summary, detail from product endpoint
  useEffect(() => {
    async function load() {
      const summary = await fetchData();
      const meta = (summary.products || []).find(x => x.slug === slug) || null;
      if (meta) setProduct(meta as Product);
      try {
        const r = await fetch(`/api/product/${slug}`);
        const p = await r.json() as Product;
        if (p && p.slug) {
          setProduct(p);
          const trusted = (p.items || []).filter(x => x.trusted !== false);
          setAllRows(buildShopRows(trusted));
        } else if (!meta) {
          setLoading(false);
          return;
        }
      } catch (e) {
        console.error('Failed to load product detail', e);
      }
      setLoading(false);
    }
    load();
  }, [slug]);

  // Filtered + sorted + paginated rows
  const displayRows = useMemo(() => {
    let r = [...allRows];
    if (inStock) r = r.filter(x => (x.stock || 0) > 0);
    if (activeSku) r = r.filter(x => x.sku_key === activeSku);
    if (sortBy === 'stock') r.sort((a, b) => b.stock - a.stock);
    else if (sortBy === 'shop') r.sort((a, b) => a.shop_name.localeCompare(b.shop_name));
    else r.sort((a, b) => a.price - b.price);
    return showAll ? r : r.slice(0, 20);
  }, [allRows, inStock, activeSku, sortBy, showAll]);

  const bestOffer = displayRows[0] || null;
  const maxPrice = allRows.length > 0 ? Math.max(...allRows.map(r => r.price)) : 0;
  const pctSaved = bestOffer && maxPrice > bestOffer.price
    ? Math.round((1 - bestOffer.price / maxPrice) * 100)
    : 0;

  // SKU tabs
  const skuTabs = useMemo(() => {
    if (!product) return [];
    const groups: Record<string, { key: string; name: string; count: number }> = {};
    for (const it of (product.items || [])) {
      if (!it.trusted) continue;
      const text = (it.title + (it.desc || '') + (it.category || '')).toLowerCase();
      const k = buildSkuKey(text);
      if (!groups[k]) groups[k] = { key: k, name: k, count: 0 };
      groups[k].count++;
    }
    return Object.values(groups).sort((a, b) => b.count - a.count);
  }, [product]);

  const topSkus = skuTabs.slice(0, 7);
  const moreSkus = skuTabs.slice(7);
  const [showMore, setShowMore] = useState(false);

  if (loading) {
    return <div className="page">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height: 40, marginBottom: 8, borderRadius: 6 }} />
      ))}
    </div>;
  }

  if (!product) return <div className="page"><p className="meta">未找到该产品</p></div>;

  return (
    <div className="page">
      {/* Header */}
      <div className="cmp-header">
        <div className="cmp-icon" dangerouslySetInnerHTML={{ __html: getBigLogo(product.type?.slug || 'other') }} />
        <div>
          <div className="cmp-title">{product.name}</div>
          <div className="cmp-meta">
            {product.type?.vendor || ''} · {product.stats?.shops} 个商家 · {product.stats?.count} 个报价 · 库存 {product.stats?.stock}
          </div>
        </div>
      </div>

      {/* Best Offer Banner */}
      {bestOffer && (
        <div className="best-offer">
          <div className="bo-label">✦ 推荐最低价</div>
          <div className="bo-price">¥{bestOffer.price.toFixed(2)}</div>
          <a href={bestOffer.shop_link} target="_blank" rel="noopener" style={{ textDecoration: 'none', color: 'inherit' }}>
            <div className="bo-shop">{bestOffer.shop_name}</div>
          </a>
          <div className="bo-title">
            {bestOffer.title.length > 60 ? bestOffer.title.substring(0, 60) + '…' : bestOffer.title}
          </div>
          {bestOffer.stock > 0 ? (
            <div className="bo-stock">库存 {bestOffer.stock} · {bestOffer.sku_key}</div>
          ) : (
            <div className="bo-stock"><span className="out-of-stock">缺货</span> · {bestOffer.sku_key}</div>
          )}
        </div>
      )}

      {/* Filter Bar */}
      <div className="filter-bar">
        <select value={sortBy} onChange={e => setSortBy(e.target.value as any)}>
          <option value="price">💰 价格排序</option>
          <option value="stock">📦 库存排序</option>
          <option value="shop">🔤 商家排序</option>
        </select>
        <label>
          <input type="checkbox" checked={inStock} onChange={e => setInStock(e.target.checked)} />
          仅看有货
        </label>
      </div>

      {/* SKU Tags */}
      {topSkus.length > 0 && (
        <div className="sku-tags">
          <span className={`sku-tag ${!activeSku ? 'active' : ''}`} onClick={() => setActiveSku('')}>
            全部 <span className="count">{product.trusted_count || product.stats?.count}</span>
          </span>
          {topSkus.map(s => (
            <span
              key={s.key}
              className={`sku-tag ${activeSku === s.key ? 'active' : ''}`}
              onClick={() => setActiveSku(activeSku === s.key ? '' : s.key)}
            >
              {s.name} <span className="count">{s.count}</span>
            </span>
          ))}
          {moreSkus.length > 0 && (
            <span className="sku-tag" onClick={() => setShowMore(!showMore)} style={{ position: 'relative' }}>
              更多 ▾
              {showMore && (
                <div style={{
                  position: 'absolute', top: '100%', left: 0, zIndex: 10,
                  background: '#fff', border: '1px solid var(--color-border)',
                  borderRadius: 6, padding: 4, boxShadow: 'var(--shadow-blue) 0px 20px 35px -20px',
                  minWidth: 180, marginTop: 4
                }}>
                  {moreSkus.map(s => (
                    <div
                      key={s.key}
                      style={{ padding: '6px 12px', fontSize: 12, cursor: 'pointer', borderRadius: 4, whiteSpace: 'nowrap' }}
                      onClick={() => {
                        setActiveSku(activeSku === s.key ? '' : s.key);
                        setShowMore(false);
                      }}
                      onMouseEnter={e => (e.currentTarget.style.background = 'rgba(83,58,253,.05)')}
                      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                    >
                      {s.name} ({s.count})
                    </div>
                  ))}
                </div>
              )}
            </span>
          )}
        </div>
      )}

      {/* Two-column: Table + Sidebar */}
      <div className="cmp-grid">
        {/* Left: Table */}
        <div className="cmp-main">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 46 }}>#</th>
                <th style={{ minWidth: 150 }}>商家</th>
                <th style={{ minWidth: 200 }}>商品</th>
                <th style={{ width: 65, textAlign: 'center' }}>库存</th>
                <th style={{ width: 110, textAlign: 'right' }}>CNY</th>
              </tr>
            </thead>
            <tbody>
              {displayRows.map((row, i) => (
                <tr key={row.shop_id}>
                  <td style={{ color: 'var(--color-body)' }}>{i + 1}</td>
                  <td>
                    <a href={row.shop_link} target="_blank" rel="noopener">{row.shop_name}</a>
                  </td>
                  <td style={{ fontSize: 12, color: 'var(--color-heading)' }}>
                    {row.title.length > 48 ? row.title.substring(0, 48) + '…' : row.title}
                  </td>
                  <td className="stock">
                    {row.stock > 0 ? row.stock : <span className="out-of-stock">缺货</span>}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                      {i === 0 && <span className="badge-best">最低</span>}
                      <span className="price">¥{row.price.toFixed(2)}</span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Footer */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
            <span className="meta">共 {displayRows.length} 个商家报价</span>
            {allRows.length > 20 && (
              <button className="btn-text" onClick={() => setShowAll(!showAll)}>
                {showAll ? '收起' : `查看全部 ${allRows.length} 个`}
              </button>
            )}
          </div>
        </div>

        {/* Right: Sidebar */}
        <div className="cmp-sidebar">
          {bestOffer && (
            <PriceHighlight
              price={bestOffer.price}
              shopName={bestOffer.shop_name}
              pctSaved={pctSaved}
            />
          )}
          {product.price_distribution && (
            <div className="sidebar-card">
              <PriceChart dist={product.price_distribution} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
