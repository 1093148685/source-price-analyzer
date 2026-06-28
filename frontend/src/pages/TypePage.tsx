import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { fetchData } from '../api';
import type { ProductType } from '../api';
import { getLogo } from '../logos';

export default function TypePage() {
  const { slug } = useParams<{ slug: string }>();
  const [loading, setLoading] = useState(true);
  const [tp, setTp] = useState<ProductType | null>(null);
  const nav = useNavigate();

  useEffect(() => {
    fetchData().then(d => {
      setTp((d.types || []).find(t => t.slug === slug) || null);
      setLoading(false);
    });
  }, [slug]);

  if (loading) {
    return (
      <div className="page">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="skeleton" style={{ height: 60, marginBottom: 12, borderRadius: 6 }} />
        ))}
      </div>
    );
  }

  if (!tp) return <div className="page"><p className="meta">未找到该产品类型</p></div>;

  return (
    <div className="page">
      <h2>{tp.name}</h2>
      <div className="product-grid">
        {(tp.products || []).map(p => (
          <div key={p.slug} className="card" onClick={() => nav(`/compare/${p.slug}`)}>
            <div className="card-header-row">
              <div className="card-icon" dangerouslySetInnerHTML={{ __html: getLogo(tp.slug) }} />
              <div style={{ minWidth: 0, flex: 1 }}>
                <div className="card-title">{p.name}</div>
                <div className="card-subtitle">{tp.vendor}</div>
              </div>
            </div>
            <div className="card-desc">
              {p.desc}。{p.stats.shops} 个商家，{p.stats.count} 个套餐，最低 ¥{p.stats.min?.toFixed(0) || '0'}
            </div>
            <div className="card-footer">
              <span className="label">{tp.name}</span>
              <span style={{ fontSize: 11, color: 'var(--color-body)', fontFamily: 'Source Code Pro, monospace' }}>
                {p.stats.count} items
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
