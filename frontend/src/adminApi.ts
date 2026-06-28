// Admin API client
const TOKEN_KEY = 'admin_token';

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || '';
}

export function setToken(t: string) {
  localStorage.setItem(TOKEN_KEY, t);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function adminFetch(path: string, init?: RequestInit): Promise<any> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string> || {}),
  };
  if (token) headers['X-Admin-Token'] = token;

  const r = await fetch(path, { ...init, headers });
  return r.json();
}

export async function login(password: string): Promise<{ ok: boolean; token?: string; error?: string }> {
  const form = new FormData();
  form.set('password', password);
  const r = await fetch('/api/admin/login', { method: 'POST', body: form });
  const data = await r.json();
  if (data.ok && data.token) setToken(data.token);
  return data;
}

export async function setup(password: string): Promise<{ ok: boolean; token?: string; error?: string }> {
  const form = new FormData();
  form.set('password', password);
  const r = await fetch('/api/admin/setup', { method: 'POST', body: form });
  const data = await r.json();
  if (data.ok && data.token) setToken(data.token);
  return data;
}

export interface HealthSummary {
  cached_items: number;
  fresh_items: number;
  gone_count: number;
  delisted_count: number;
  price_changed_count: number;
  new_items_count: number;
  empty_shops_count: number;
  low_stock_shops_count: number;
}

export interface HealthRecord {
  ts: number;
  datetime: string;
  summary: HealthSummary;
}

export interface ScheduleStatus {
  enabled: boolean;
  cron: string;
  timezone: string;
  next_run: string | null;
  running: boolean;
}

export interface HealthStatus {
  ok: boolean;
  latest?: any;
  history: HealthRecord[];
  schedule: ScheduleStatus;
}
