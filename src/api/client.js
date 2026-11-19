// Data layer: the only place the UI talks to the TruthLens backend (served under /api).
// VITE_API_BASE points a hosted build at the backend (e.g. https://user-truthlens.hf.space); empty = same origin.
import { useCallback, useEffect, useRef, useState } from 'react';

export let API_BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');
const TOKEN_KEY = 'tl-token';

// Quick Tunnel addresses change after a demo restart. An open tab can recover the
// latest public address from its own deployment without reloading the app.
let addressRefresh;
async function refreshApiAddress() {
  if (!import.meta.env.PROD) return;
  if (!addressRefresh) addressRefresh = (async () => {
    const response = await fetch('/api-config.json', { cache: 'no-store' });
    if (!response.ok) return;
    const config = await response.json();
    if (typeof config.apiBase !== 'string') return;
    const base = config.apiBase.replace(/\/$/, '');
    if (base && new URL(base).protocol !== 'https:') return;
    API_BASE = base;
  })().catch(() => {}).finally(() => { addressRefresh = null; });
  await addressRefresh;
}

async function serviceFetch(path, opts = {}, retrySafe = true) {
  const previousBase = API_BASE;
  try {
    return await fetch(`${previousBase}${path}`, opts);
  } catch (error) {
    await refreshApiAddress();
    // Do not repeat writes: the server may have saved them before the connection failed.
    if (!retrySafe || API_BASE === previousBase) throw error;
    return fetch(`${API_BASE}${path}`, opts);
  }
}

export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}
export function setToken(token) {
  try { if (token) localStorage.setItem(TOKEN_KEY, token); else localStorage.removeItem(TOKEN_KEY); } catch { /* storage unavailable */ }
}

async function request(method, path, body, isForm = false) {
  const opts = { method, headers: {} };
  const token = getToken();
  if (token) opts.headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) {
    if (isForm) opts.body = body;
    else { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  }
  let res;
  try {
    res = await serviceFetch(`/api${path}`, opts, method === 'GET' || path === '/auth/login');
  } catch {
    throw Object.assign(new Error('Could not reach the analysis service. Refresh this page and try again. The demo Mac must be awake and online.'), { status: 0 });
  }
  const text = await res.text();
  const data = text ? (() => { try { return JSON.parse(text); } catch { return text; } })() : null;
  if (!res.ok) {
    if (res.status === 401 && !path.startsWith('/auth/')) window.dispatchEvent(new Event('tl-unauthorized'));
    const detail = data && typeof data === 'object' ? data.detail : null;
    const msg = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d) => d.msg).join('; ')
      : res.status >= 500 ? 'The analysis service had a problem. Try again in a moment.' : `${res.status} ${res.statusText}`;
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return data;
}

/** Fetch a protected file (media, heatmap, report) and return an object URL usable in <img>, <video>, <audio>. */
export function useMediaUrl(path) {
  const [url, setUrl] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    if (!path) { setUrl(null); return undefined; }
    let alive = true, made = null;
    setError(null);
    const token = getToken();
    serviceFetch(path, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => (r.ok ? r.blob() : Promise.reject(Object.assign(new Error(`${r.status}`), { status: r.status }))))
      .then((b) => { if (alive) { made = URL.createObjectURL(b); setUrl(made); } })
      .catch((e) => { if (alive) { setUrl(null); setError(e); } });
    return () => { alive = false; if (made) URL.revokeObjectURL(made); };
  }, [path]);
  return { url, error };
}

/** Download a protected file (report PDF / JSON) through fetch, so the auth header is sent. */
export async function download(path, filename) {
  const token = getToken();
  const r = await serviceFetch(path, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!r.ok) throw new Error(`Download failed (${r.status})`);
  const href = URL.createObjectURL(await r.blob());
  const a = Object.assign(document.createElement('a'), { href, download: filename });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(href), 10000);
}

export const api = {
  get: (p) => request('GET', p),
  post: (p, b) => request('POST', p, b ?? {}),
  patch: (p, b) => request('PATCH', p, b),
  put: (p, b) => request('PUT', p, b),
  upload(caseId, file) {
    const fd = new FormData();
    fd.append('file', file);
    return request('POST', `/cases/${caseId}/evidence`, fd, true);
  },
  addText(caseId, text, source) {
    const fd = new FormData();
    fd.append('text', text);
    if (source) fd.append('source', source);
    return request('POST', `/cases/${caseId}/evidence`, fd, true);
  },
};

/** Fetch `path` (null = skip). Re-fetches when `path` or `reloadKey` change; `poll` ms keeps it fresh. */
export function useApi(path, { poll = 0, reloadKey = 0, enabled = true } = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: !!path });
  const seq = useRef(0);
  const load = useCallback(() => {
    if (!path || !enabled) return Promise.resolve();
    const n = ++seq.current;
    return api.get(path).then(
      (data) => { if (n === seq.current) setState({ data, error: null, loading: false }); },
      (error) => { if (n === seq.current) setState((s) => ({ data: s.data, error, loading: false })); },
    );
  }, [path, enabled]);
  useEffect(() => {
    if (!path || !enabled) { setState({ data: null, error: null, loading: false }); return undefined; }
    setState((s) => ({ ...s, loading: true }));
    load();
    if (!poll) return undefined;
    const iv = setInterval(load, poll);
    return () => clearInterval(iv);
  }, [load, poll, reloadKey, path, enabled]);
  return { ...state, reload: load, setData: (d) => setState((s) => ({ ...s, data: typeof d === 'function' ? d(s.data) : d })) };
}

// ---- small formatting helpers shared by screens

export const fmtT = (t) => {
  const m = Math.floor(t / 60);
  const s = t - m * 60;
  return `${String(m).padStart(2, '0')}:${s.toFixed(1).padStart(4, '0')}`;
};

export function relTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
  const s = (Date.now() - d.getTime()) / 1000;
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  if (s < 172800) return 'Yesterday';
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
}

export const fmtDate = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
};

export const fmtBytes = (n) => (n >= 1e9 ? `${(n / 1e9).toFixed(1)} GB` : n >= 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.round(n / 1e3)} KB`);

export const shortHash = (h) => (h && h.length > 12 ? `${h.slice(0, 8)}…${h.slice(-4)}` : h || '—');

/** "local" (analysis on this machine) or "hosted" (analysis on the TruthLens server); drives the privacy copy. */
export function useServerMode() {
  const h = useApi('/health');
  return h.data?.mode || (API_BASE ? 'hosted' : 'local');
}

// Every place the UI says where analysis happens or where evidence goes reads from here.
export const PRIVACY = {
  local: {
    badge: 'Running locally · ₹0', detail: 'No data leaves this device', short: 'Local · ₹0', home: 'Runs locally · No data leaves this device',
    where: 'on this device', worker: 'one worker on this device · no network', account: 'Sign up · free · account on this device',
    pointTitle: 'Runs on your device', pointText: 'Files are hashed on arrival and originals stay read-only. Nothing is uploaded.',
    hero: 'TruthLens analyzes your evidence on this device, shows',
    analyzeStep: 'Run image, video, audio and text analyzers locally.', settings: 'Settings · this device',
  },
  hosted: {
    badge: 'Hosted analysis server', detail: 'Evidence is stored on the server, visible only to your account', short: 'Hosted',
    home: 'Hosted demo · Your evidence is visible only to your account',
    where: 'on the TruthLens server', worker: 'one worker on the TruthLens server · no outside services',
    account: 'Sign up · free · hosted demo account',
    pointTitle: 'Private to your account', pointText: 'Files are uploaded to the TruthLens server, hashed on arrival and kept read-only. Only your account can see them.',
    hero: 'TruthLens analyzes the evidence you upload on its own server, shows',
    analyzeStep: 'Run image, video, audio and text analyzers on the TruthLens server.', settings: 'Settings · your account',
  },
};
