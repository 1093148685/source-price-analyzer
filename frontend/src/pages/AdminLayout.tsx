import { useEffect, useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { adminFetch, getToken, clearToken } from '../adminApi';

export default function AdminLayout() {
  const [authed, setAuthed] = useState<boolean | null>(null);
  const nav = useNavigate();
  const loc = useLocation();

  useEffect(() => {
    if (!getToken()) { setAuthed(false); return; }
    adminFetch('/api/admin/check-auth').then(d => {
      setAuthed(d.ok);
    }).catch(() => setAuthed(false));
  }, []);

  const handleLogout = () => {
    adminFetch('/api/admin/logout', { method: 'POST' });
    clearToken();
    nav('/admin/login');
  };

  if (authed === null) return <div className="page"><p className="meta">验证中...</p></div>;
  if (authed === false) { nav('/admin/login'); return null; }

  const navItems = [
    { path: '/admin', label: '🔍 安全检测', exact: true },
  ];

  return (
    <div className="admin-layout">
      <aside className="admin-sidebar">
        <div className="admin-sidebar-header">
          <h3>管理后台</h3>
        </div>
        <nav className="admin-nav">
          {navItems.map(item => (
            <a
              key={item.path}
              className={`admin-nav-item ${loc.pathname === item.path ? 'active' : ''}`}
              onClick={() => nav(item.path)}
            >
              {item.label}
            </a>
          ))}
        </nav>
        <div className="admin-sidebar-footer">
          <a className="admin-nav-item" onClick={handleLogout}>退出登录</a>
        </div>
      </aside>
      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  );
}
