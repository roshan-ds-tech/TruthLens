// Data layer: the only place the UI talks to the TruthLens backend (served under /api).
import { useCallback, useEffect, useRef, useState } from 'react';

async function request(method, path, body, isForm = false) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    if (isForm) opts.body = body;
    else { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  }
  const res = await fetch(`/api${path}`, opts);
  const text = await res.text();
  const data = text ? (() => { try { return JSON.parse(text); } catch { return text; } })() : null;
  if (!res.ok) {
    const err = new Error((data && data.detail) || `${res.status} ${res.statusText}`);
    err.status = res.status;
    throw err;
  }
  return data;
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
