import { useEffect, useState } from 'react';
import { adminFetch } from '../adminApi';
import type { HealthStatus, HealthRecord } from '../adminApi';

function SummaryCard({ label, value, color }: { label: string; value: number | string; color?: string }) {
  return (
    <div className="summary-card">
      <div className="summary-value" style={color ? { color } : {}}>{value}</div>
      <div className="summary-label">{label}</div>
    </div>
  );
}

function HistoryTable({ records }: { records: HealthRecord[] }) {
  if (!records.length) return <p className="meta">暂无检测记录</p>;
  return (
    <table className="data-table" style={{ marginTop: 0 }}>
      <thead>
        <tr>
          <th>时间</th>
          <th>缓存</th>
          <th>在线</th>
          <th>变动</th>
          <th>下架</th>
          <th>未上架</th>
        </tr>
      </thead>
      <tbody>
        {records.map((r) => (
          <tr key={r.ts}>
            <td style={{ fontSize: 12 }}>{r.datetime?.replace('T', ' ').substring(0, 19)}</td>
            <td>{r.summary.cached_items}</td>
            <td>{r.summary.fresh_items}</td>
            <td style={{ color: r.summary.price_changed_count > 0 ? 'var(--color-danger)' : 'var(--color-success-text)' }}>
              {r.summary.price_changed_count}
            </td>
            <td style={{ color: r.summary.gone_count > 0 ? 'var(--color-danger)' : 'var(--color-body)' }}>
              {r.summary.gone_count}
            </td>
            <td style={{ color: r.summary.delisted_count > 0 ? 'var(--color-danger)' : 'var(--color-body)' }}>
              {r.summary.delisted_count}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SchedulePanel({ status, onUpdate }: { status: any; onUpdate: () => void }) {
  const [enabled, setEnabled] = useState(status?.enabled || false);
  const [cron, setCron] = useState(status?.cron || '0 19 * * *');
  const [tz, setTz] = useState(status?.timezone || 'Asia/Shanghai');
  const [msg, setMsg] = useState('');

  const save = async () => {
    const form = new FormData();
    form.set('enabled', String(enabled));
    form.set('cron', cron);
    form.set('timezone', tz);
    const r = await adminFetch('/api/admin/health/schedule', { method: 'POST', body: form });
    if (r.ok) {
      setMsg('已保存');
      onUpdate();
    } else {
      setMsg('保存失败: ' + (r.error || ''));
    }
  };

  return (
    <div className="sidebar-card" style={{ marginTop: 16 }}>
      <h4 style={{ marginBottom: 12 }}>⏰ 定时检测</h4>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} />
          启用定时检测
        </label>
        <div className="form-row">
          <span className="meta">Cron:</span>
          <input className="form-input" value={cron} onChange={e => setCron(e.target.value)}
                 style={{ flex: 1, fontFamily: 'Source Code Pro, monospace', fontSize: 12 }} />
        </div>
        <div className="form-row">
          <span className="meta">时区:</span>
          <select className="form-select" value={tz} onChange={e => setTz(e.target.value)} style={{ flex: 1 }}>
            <option value="Asia/Shanghai">Asia/Shanghai (UTC+8)</option>
            <option value="UTC">UTC</option>
            <option value="Asia/Tokyo">Asia/Tokyo</option>
            <option value="America/New_York">America/New_York</option>
          </select>
        </div>
        {status?.next_run && (
          <p className="meta">下次执行: {new Date(status.next_run + 'Z').toLocaleString('zh-CN')}</p>
        )}
        <button className="btn-primary" onClick={save} style={{ marginTop: 4 }}>保存设置</button>
        {msg && <p className="meta" style={{ color: msg.includes('失败') ? 'var(--color-danger)' : 'var(--color-success-text)' }}>{msg}</p>}
      </div>
    </div>
  );
}

export default function AdminHealth() {
  const [status, setStatus] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<{ step: string; message: string } | null>(null);

  const loadStatus = async () => {
    try {
      const data = await adminFetch('/api/admin/health/status');
      if (data.ok) setStatus(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => { loadStatus(); }, []);

  const runCheck = async () => {
    setRunning(true);
    setProgress({ step: 'start', message: '启动检测...' });

    // Poll for progress
    const pollInterval = setInterval(async () => {
      try {
        const data = await adminFetch('/api/admin/health/progress');
        if (data.ok && data.progress?.running) {
          setProgress({ step: data.progress.step, message: data.progress.message });
        }
      } catch (e) {}
    }, 800);

    try {
      const data = await adminFetch('/api/admin/health/run', { method: 'POST' });
      clearInterval(pollInterval);
      if (data.ok) {
        setProgress({ step: 'done', message: '检测完成 ✓' });
        loadStatus();
      } else {
        setProgress({ step: 'error', message: '检测失败: ' + (data.error || '') });
      }
    } catch (e: any) {
      clearInterval(pollInterval);
      setProgress({ step: 'error', message: '检测失败: ' + e.message });
    }
    setRunning(false);
    setTimeout(() => setProgress(null), 3000);
  };

  const s = status?.latest?.summary;

  if (loading) return <div className="page"><p className="meta">加载中...</p></div>;

  return (
    <div>
      <h2>🔍 安全检测</h2>
      <p className="meta" style={{ marginBottom: 20 }}>商品健康状态、价格变动、下架监控</p>

      {/* Action Bar */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, alignItems: 'center', flexWrap: 'wrap' }}>
        <button className="btn-primary" onClick={runCheck} disabled={running}>
          {running ? '⏳ 检测中...' : '🔄 立即检测'}
        </button>
        {/* Progress Steps */}
        {progress && (
          <div className="progress-steps">
            {[
              { key: 'loading_cache', label: '加载缓存' },
              { key: 'indexing', label: '构建索引' },
              { key: 'login', label: '登录平台' },
              { key: 'fetching_goods', label: '拉取商品' },
              { key: 'fetching_merchants', label: '拉取商家' },
              { key: 'comparing', label: '数据对比' },
            ].map(s => (
              <span
                key={s.key}
                className={`progress-step ${
                  progress.step === s.key ? 'active' :
                  progress.step === 'done' ? 'done' :
                  progress.step === 'error' ? 'error' :
                  ''
                }`}
              >
                {progress.step === s.key ? '⏳' :
                 progress.step === 'done' ? '✓' :
                 progress.step === 'error' ? '✗' : '○'} {s.label}
              </span>
            ))}
            {progress.step === 'done' && <span className="progress-step done">✓ 完成</span>}
            {progress.step === 'error' && <span className="progress-step error">✗ {progress.message}</span>}
          </div>
        )}
      </div>

      {/* Summary Cards */}
      {s && (
        <div className="summary-grid">
          <SummaryCard label="在线商品" value={s.fresh_items} color="var(--color-success-text)" />
          <SummaryCard label="缓存商品" value={s.cached_items} />
          <SummaryCard label="价格变动" value={s.price_changed_count} color={s.price_changed_count > 0 ? 'var(--color-danger)' : 'var(--color-body)'} />
          <SummaryCard label="已下架" value={s.gone_count} color={s.gone_count > 0 ? 'var(--color-danger)' : 'var(--color-body)'} />
          <SummaryCard label="未上架" value={s.delisted_count} color={s.delisted_count > 0 ? 'var(--color-danger)' : 'var(--color-body)'} />
          <SummaryCard label="空店铺" value={s.empty_shops_count} />
        </div>
      )}

      {/* No data state */}
      {!s && <p className="meta" style={{ padding: '40px 0', textAlign: 'center' }}>暂无检测数据，点击「立即检测」开始</p>}

      {/* Schedule Panel */}
      {status?.schedule && (
        <SchedulePanel status={status.schedule} onUpdate={loadStatus} />
      )}

      {/* History */}
      <div style={{ marginTop: 24 }}>
        <h4 style={{ marginBottom: 12 }}>📋 检测历史</h4>
        <HistoryTable records={status?.history || []} />
      </div>
    </div>
  );
}
