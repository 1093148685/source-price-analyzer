import { useState } from 'react';

interface CategoryGroup {
  type_slug: string;
  type_name: string;
  sub_slug: string;
  sub_name: string;
  confidence: number;
  items: { id: string; title: string; price: number; stock: number; link: string; trusted: boolean }[];
}

interface ShopResult {
  found: boolean;
  total?: number;
  categories?: CategoryGroup[];
}

export default function ShopAnalyzer() {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Record<string, ShopResult> | null>(null);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const analyze = async () => {
    const urls = input
      .split(/[\n,]+/)
      .map(s => s.trim())
      .filter(Boolean);
    if (!urls.length) return;

    setLoading(true);
    setError('');
    setResults(null);

    try {
      const resp = await fetch('/api/analyze-shop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls }),
      });
      const data = await resp.json();
      if (data.ok) {
        setResults(data.results);
      } else {
        setError(data.error || '解析失败');
      }
    } catch (e) {
      setError('网络错误');
    }
    setLoading(false);
  };

  const toggle = (slug: string) => {
    setExpanded(prev => ({ ...prev, [slug]: !prev[slug] }));
  };

  const getTypeEmoji = (slug: string) => {
    const map: Record<string, string> = {
      chatgpt: '🤖', 'codex-api': '🔑', 'microsoft-email': '📧', claude: '🧠',
      grok: '𝕏', gemini: '💎', cursor: '🖱️', 'dev-tools': '🛠️',
      lessons: '📚', 'virtual-cards': '💳', gcp: '☁️', 'proxy-vpn': '🌐',
      'apple-misc': '🎫', apple: '🍎', netflix: '🎬', 'cloud-drive': '☁️',
    };
    return map[slug] || '📦';
  };

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '24px 16px' }}>
      <h2 style={{ fontSize: 20, fontWeight: 600, margin: '0 0 8px' }}>🔍 店铺商品解析</h2>
      <p style={{ color: 'var(--color-body)', fontSize: 13, marginBottom: 16 }}>
        输入店铺链接（支持多个，换行或逗号分隔），自动拉取商品并归类
      </p>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder={'https://pay.ldxp.cn/shop/haozi719\nhttps://pay.ldxp.cn/shop/mdkj'}
          rows={3}
          style={{
            flex: 1, padding: '10px 12px', borderRadius: 6,
            border: '1px solid var(--color-border, #e0e0e0)',
            background: 'var(--color-bg, #fff)', color: 'var(--color-heading, #111)',
            fontSize: 13, fontFamily: 'monospace', resize: 'vertical',
          }}
        />
        <button
          onClick={analyze}
          disabled={loading || !input.trim()}
          style={{
            padding: '10px 20px', borderRadius: 6, border: 'none',
            background: loading ? '#ccc' : 'var(--color-primary, #635bff)',
            color: '#fff', fontWeight: 600, cursor: loading ? 'default' : 'pointer',
            fontSize: 14, whiteSpace: 'nowrap',
          }}
        >
          {loading ? '解析中...' : '解析'}
        </button>
      </div>

      {error && (
        <div style={{ padding: 12, borderRadius: 6, background: 'rgba(234,34,97,.08)', color: '#ea2261', fontSize: 13, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {results && Object.entries(results).map(([slug, result]) => (
        <div key={slug} style={{
          marginBottom: 16, border: '1px solid var(--color-border, #e0e0e0)',
          borderRadius: 8, overflow: 'hidden',
        }}>
          <div
            onClick={() => toggle(slug)}
            style={{
              padding: '12px 16px', background: 'var(--color-bg-secondary, #f5f5f5)',
              cursor: 'pointer', display: 'flex', justifyContent: 'space-between',
              alignItems: 'center', userSelect: 'none',
            }}
          >
            <div>
              <span style={{ fontWeight: 600, fontSize: 14 }}>🏪 {slug}</span>
              {result.found ? (
                <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--color-body)' }}>
                  {result.total} 件商品 · {result.categories?.length || 0} 个分类
                </span>
              ) : (
                <span style={{ marginLeft: 8, fontSize: 12, color: '#ea2261' }}>未找到</span>
              )}
            </div>
            <span style={{ fontSize: 16, color: 'var(--color-body)' }}>
              {expanded[slug] ? '▾' : '▸'}
            </span>
          </div>

          {expanded[slug] && result.categories && (
            <div style={{ padding: '8px 16px 16px' }}>
              {result.categories.map(cat => (
                <div key={cat.type_slug + cat.sub_slug} style={{ marginBottom: 12 }}>
                  <div style={{
                    fontSize: 13, fontWeight: 600, marginBottom: 4, padding: '4px 0',
                    borderBottom: '1px solid var(--color-border, #eee)',
                  }}>
                    {getTypeEmoji(cat.type_slug)} {cat.type_name} › {cat.sub_name}
                    <span style={{ fontWeight: 400, color: 'var(--color-body)', marginLeft: 8 }}>
                      {cat.items.length} 件
                    </span>
                    {cat.confidence < 0.5 && (
                      <span style={{ marginLeft: 6, fontSize: 10, color: '#f59e0b' }}>低置信度</span>
                    )}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {cat.items.slice(0, 10).map((item, i) => (
                      <div key={i} style={{
                        display: 'flex', alignItems: 'center', gap: 8,
                        fontSize: 12, padding: '2px 4px',
                      }}>
                        <span style={{
                          minWidth: 52, textAlign: 'right',
                          fontFamily: 'monospace', fontWeight: 600,
                          color: 'var(--color-heading)',
                        }}>
                          ¥{item.price.toFixed(2)}
                        </span>
                        <span style={{
                          flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                          color: item.trusted ? 'var(--color-body)' : '#ea2261',
                        }}>
                          {item.title}
                        </span>
                        {item.stock === 0 && (
                          <span style={{
                            fontSize: 10, color: '#f59e0b',
                            background: 'rgba(245,158,11,.1)', padding: '1px 4px', borderRadius: 3,
                          }}>缺货</span>
                        )}
                        <a href={item.link} target="_blank" rel="noopener"
                          style={{ fontSize: 11, color: 'var(--color-primary, #635bff)', textDecoration: 'none' }}>
                          查看 →
                        </a>
                      </div>
                    ))}
                    {cat.items.length > 10 && (
                      <div style={{ fontSize: 11, color: 'var(--color-body)', padding: '2px 4px' }}>
                        ... 还有 {cat.items.length - 10} 件
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}

      {results && Object.keys(results).length === 0 && (
        <div style={{ color: 'var(--color-body)', fontSize: 13 }}>无结果</div>
      )}
    </div>
  );
}
