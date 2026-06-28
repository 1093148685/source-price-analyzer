import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, setup } from '../adminApi';

export default function AdminLogin() {
  const [pw, setPw] = useState('');
  const [msg, setMsg] = useState('');
  const [mode, setMode] = useState<'login' | 'setup'>('login');
  const nav = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg('');
    if (!pw || pw.length < 4) { setMsg('密码至少4位'); return; }

    const result = mode === 'setup' ? await setup(pw) : await login(pw);
    if (result.ok) {
      setMsg('登录成功');
      setTimeout(() => nav('/admin'), 300);
    } else {
      if (result.error?.includes('已设置过密码')) {
        setMode('login');
        setMsg('已设置过密码，请登录');
      } else {
        setMsg(result.error || '操作失败');
      }
    }
  };

  return (
    <div className="page" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh' }}>
      <div className="sidebar-card" style={{ width: 360, padding: 32 }}>
        <h2 style={{ marginBottom: 8 }}>管理后台</h2>
        <p className="meta" style={{ marginBottom: 24 }}>
          {mode === 'setup' ? '首次使用，设置管理员密码' : '请输入管理员密码'}
        </p>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            className="form-input"
            placeholder="管理员密码"
            value={pw}
            onChange={e => setPw(e.target.value)}
            autoFocus
            style={{ width: '100%', marginBottom: 12 }}
          />
          <button type="submit" className="btn-primary" style={{ width: '100%', marginBottom: 8 }}>
            {mode === 'setup' ? '设置密码' : '登录'}
          </button>
        </form>
        {msg && <p className="meta" style={{ color: msg.includes('成功') ? 'var(--color-success-text)' : 'var(--color-danger)', marginTop: 8 }}>{msg}</p>}
        <p className="meta" style={{ marginTop: 16, textAlign: 'center', cursor: 'pointer' }}
           onClick={() => setMode(mode === 'login' ? 'setup' : 'login')}>
          {mode === 'login' ? '首次使用？设置密码' : '已有密码？去登录'}
        </p>
      </div>
    </div>
  );
}
