import { useNavigate } from 'react-router-dom';

export default function HomePage() {
  const nav = useNavigate();
  return (
    <div className="page" style={{ textAlign: 'center', paddingTop: 160 }}>
      <h1 style={{
        fontSize: 48, fontWeight: 300, color: 'var(--color-heading)',
        letterSpacing: '-.96px', marginBottom: 16
      }}>
        Source Price
      </h1>
      <p style={{
        fontSize: 18, fontWeight: 300, color: 'var(--color-body)',
        marginBottom: 32, lineHeight: 1.5
      }}>
        全球 AI 订阅货源 · 实时比价
      </p>
      <button
        onClick={() => nav('/products')}
        style={{
          fontSize: 15, fontWeight: 400, color: '#fff',
          background: 'var(--color-accent)', border: 'none',
          padding: '10px 28px', borderRadius: 4, cursor: 'pointer'
        }}
      >
        查看所有订阅
      </button>
    </div>
  );
}
