import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchData, aggregateType, fmtPrice } from '../api';
import type { ProductType, AggStats } from '../api';
import { getLogo } from '../logos';

export default function ProductsPage() {
  const [loading, setLoading] = useState(true);
  const [types, setTypes] = useState<(ProductType & { agg: AggStats })[]>([]);
  const nav = useNavigate();

  useEffect(() => {
    fetchData().then(d => {
      setTypes((d.types || []).map(t => ({ ...t, agg: aggregateType(t) })));
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="page">
        <h2>应用列表</h2>
        <div className="product-grid">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="card">
              <div className="skeleton" style={{ height: 80, marginBottom: 12 }} />
              <div className="skeleton" style={{ height: 16, width: '60%', marginBottom: 8 }} />
              <div className="skeleton" style={{ height: 14, width: '40%' }} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <h2>应用列表</h2>
      <div className="product-grid">
        {types.map(t => (
          <div key={t.slug} className="card" onClick={() => nav(`/product/${t.slug}`)}>
            <div className="card-header-row">
              <div className="card-icon" dangerouslySetInnerHTML={{ __html: getLogo(t.slug) }} />
              <div style={{ minWidth: 0, flex: 1 }}>
                <div className="card-title">{t.name}</div>
                <div className="card-subtitle">{t.vendor} · {t.agg.productCount} 个订阅类型</div>
              </div>
            </div>
            <div className="card-desc">
              {t.agg.minPrice > 0 ? `最低 ${fmtPrice(t.agg.minPrice)} · ` : ''}
              {t.agg.shopCount} 个商家 · {t.agg.totalItems} 个套餐
            </div>
            <div className="card-footer">
              <span className="label">{t.name}</span>
              <span style={{ fontSize: 11, color: 'var(--color-body)', fontFamily: 'Source Code Pro, monospace' }}>
                {t.agg.shopCount} shops
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
