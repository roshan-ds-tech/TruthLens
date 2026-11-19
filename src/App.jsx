import { useEffect, useRef, useState } from 'react';
import { c, THEMES, YELLOW, YELLOW_HOVER, MONO, Icon, Logo, hover } from './ui.jsx';
import Home from './screens/Home.jsx';
import Dashboard from './screens/Dashboard.jsx';
import Cases from './screens/Cases.jsx';
import EvidenceLibrary from './screens/EvidenceLibrary.jsx';
import Validation from './screens/Validation.jsx';
import Settings from './screens/Settings.jsx';
import NewCase from './screens/NewCase.jsx';
import Analysis from './screens/Analysis.jsx';
import CaseWorkspace from './screens/CaseWorkspace.jsx';
import ImageViewer from './screens/ImageViewer.jsx';
import AudioViewer from './screens/AudioViewer.jsx';
import TextViewer from './screens/TextViewer.jsx';
import ReportPreview from './screens/ReportPreview.jsx';
import { api, useApi, getToken, setToken, useServerMode, PRIVACY } from './api/client.js';

const SCREENS = ['dashboard', 'cases', 'library', 'validation', 'settings', 'newcase', 'analysis', 'workspace', 'image', 'audio', 'text', 'report'];

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: 'space_dashboard' },
  { id: 'cases', label: 'Cases', icon: 'folder_open' },
  { id: 'library', label: 'Evidence Library', icon: 'photo_library' },
  { id: 'validation', label: 'Validation', icon: 'fact_check' },
  { id: 'settings', label: 'Settings', icon: 'settings' },
];

const CASE_NAV = [
  { id: 'workspace', label: 'Workspace', icon: 'center_focus_strong' },
  { id: 'analysis', label: 'Analysis run', icon: 'motion_photos_on' },
  { id: 'image', label: 'Image evidence', icon: 'image' },
  { id: 'audio', label: 'Audio evidence', icon: 'graphic_eq' },
  { id: 'text', label: 'Text evidence', icon: 'notes' },
  { id: 'report', label: 'Report', icon: 'description' },
];

function readTheme() {
  try { return localStorage.getItem('tl-theme') || 'light'; } catch { return 'light'; }
}

// Optional URL overrides for previewing: ?screen=workspace&viewport=tablet
function readParams() {
  const p = new URLSearchParams(window.location.search);
  return { start: p.get('screen') || 'home', viewport: p.get('viewport') || 'desktop' };
}

export default function App() {
  const [{ start, viewport }] = useState(readParams);
  const [theme, setTheme] = useState(readTheme);
  // Signed in when a stored session token is still accepted by the server (checked on load).
  const [authed, setAuthed] = useState(false);
  const [checking, setChecking] = useState(() => !!getToken());
  useEffect(() => {
    if (!getToken()) return;
    api.get('/auth/me').then(() => setAuthed(true), () => setToken(null)).finally(() => setChecking(false));
  }, []);
  useEffect(() => {
    const out = () => { setToken(null); setAuthed(false); setNav({ caseId: null, evidenceId: null, jobId: null }); };
    window.addEventListener('tl-unauthorized', out);
    return () => window.removeEventListener('tl-unauthorized', out);
  }, []);
  const [screen, setScreen] = useState(start === 'home' || !SCREENS.includes(start) ? 'dashboard' : start);
  const [collapsed, setCollapsed] = useState(false);
  const [width, setWidth] = useState(() => window.innerWidth);
  // Open case, selected evidence item and analysis job; set by go(screen, { caseId, evidenceId, jobId }).
  const [nav, setNav] = useState({ caseId: null, evidenceId: null, jobId: null, draftId: null });
  const [dataVersion, setDataVersion] = useState(0);
  const [query, setQuery] = useState('');           // top-bar search, shown as results on the Cases screen
  const searchRef = useRef(null);
  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); searchRef.current?.focus(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
  const privacy = PRIVACY[useServerMode()];
  const settings = useApi(authed ? '/settings' : null, { reloadKey: dataVersion });
  const investigator = settings.data?.investigator || '';
  const initials = investigator.split(/\s+/).filter(Boolean).map((w) => w[0]).join('').slice(0, 2).toUpperCase();

  useEffect(() => {
    if (!authed || nav.caseId) return;
    api.get('/cases').then((cases) => { if (cases.length) setNav((n) => (n.caseId ? n : { ...n, caseId: cases[0].id })); }, () => {});
  }, [authed, nav.caseId]);
  const mainRef = useRef(null);

  useEffect(() => {
    const onResize = () => setWidth(window.innerWidth);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => { document.body.style.background = THEMES[theme]['--tl-bg']; }, [theme]);

  const tablet = viewport === 'tablet';
  const expanded = !(tablet || collapsed || width < 900);   // narrow windows get the icon-only sidebar
  const wideBar = expanded && width >= 1240;

  const go = (s, opts = {}) => {
    if (Object.keys(opts).length) setNav((n) => ({ ...n, ...opts }));
    if (opts.caseId || opts.jobId || opts.refresh) setDataVersion((v) => v + 1);
    setScreen(s);
    if (mainRef.current) mainRef.current.scrollTop = 0;
  };
  const toggleTheme = () => setTheme((t) => {
    const next = t === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('tl-theme', next); } catch { /* storage unavailable */ }
    return next;
  });

  const activeTop = screen === 'newcase' ? 'cases' : screen;
  const ownPrimary = ['newcase', 'analysis', 'workspace', 'report'].includes(screen);
  const is = (k) => authed && k === screen;
  const shown = (k) => ({ display: k === screen ? 'block' : 'none' });

  const rootStyle = { minHeight: '100vh', background: 'var(--tl-bg)', color: 'var(--tl-ink)', colorScheme: theme, ...THEMES[theme] };

  if (checking) return <div style={rootStyle} />;
  if (!authed) {
    return (
      <div style={rootStyle}>
        <Home theme={theme} onToggleTheme={toggleTheme} onEnter={() => { setAuthed(true); setScreen(start !== 'home' && SCREENS.includes(start) ? start : 'dashboard'); setDataVersion((v) => v + 1); }} />
      </div>
    );
  }

  const navBtn = (n, on, { h, fs, fw, iconSize, iconColor, bg, hoverBg }) => (
    <button
      key={n.id}
      onClick={() => go(n.id)}
      title={n.label}
      {...hover({ bg: hoverBg }, { display: 'flex', alignItems: 'center', gap: 12, height: h, padding: '0 12px', borderRadius: 999, border: 'none', background: bg, color: on && bg === YELLOW ? '#111111' : c.ink, fontFamily: 'inherit', fontSize: fs, fontWeight: fw, cursor: 'pointer', textAlign: 'left', width: '100%', whiteSpace: 'nowrap' })}
    >
      <Icon name={n.icon} size={iconSize} style={{ flex: 'none', color: iconColor }} />
      {expanded && <span>{n.label}</span>}
    </button>
  );

  const footBtn = (label, icon, onClick, title) => (
    <button onClick={onClick} title={title} {...hover({ bg: c.hover }, { display: 'flex', alignItems: 'center', gap: 12, height: 36, padding: '0 12px', borderRadius: 999, border: 'none', background: 'transparent', color: c.ink2, fontFamily: 'inherit', fontSize: 13, fontWeight: 600, cursor: 'pointer', width: '100%' })}>
      <Icon name={icon} style={{ flex: 'none' }} />
      {expanded && <span>{label}</span>}
    </button>
  );

  return (
    <div style={rootStyle}>
      <div style={{ minHeight: '100vh', background: tablet ? c.border : c.bg, display: 'flex', justifyContent: 'center', alignItems: 'flex-start', padding: tablet ? 32 : 0 }}>
        <div style={{ width: tablet ? 834 : '100%', maxWidth: '100%', height: tablet ? 1112 : '100vh', display: 'flex', background: c.bg, borderRadius: tablet ? 24 : 0, overflow: 'hidden', boxShadow: tablet ? '0 20px 60px rgba(17,17,17,.12)' : 'none', transform: 'translateZ(0)' }}>
          <aside style={{ width: expanded ? 248 : 72, flex: 'none', background: c.surface, borderRight: `1px solid ${c.border}`, display: 'flex', flexDirection: 'column', padding: '16px 12px', gap: 2, transition: 'width .2s ease' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 5px 22px' }}>
              <Logo />
              {expanded && (
                <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.1 }}>
                  <span style={{ fontSize: 17, fontWeight: 700, letterSpacing: '-0.018em' }}>TruthLens</span>
                  <span style={{ fontSize: 11, color: c.ink2, fontWeight: 600 }}>Forensic workstation</span>
                </div>
              )}
            </div>
            {NAV.map((n) => {
              const on = n.id === activeTop;
              return navBtn(n, on, { h: 40, fs: 14, fw: on ? 700 : 600, iconSize: 20, bg: on ? YELLOW : 'transparent', hoverBg: on ? YELLOW_HOVER : c.hover });
            })}
            <div style={{ height: 1, background: c.border, margin: '16px 6px' }} />
            {expanded && (
              <div style={{ padding: '0 12px 8px', fontSize: 10.5, fontWeight: 700, letterSpacing: '.12em', textTransform: 'uppercase', color: c.ink2 }}>
                Open case · <span style={{ fontFamily: MONO, letterSpacing: 0 }}>{nav.caseId || '—'}</span>
              </div>
            )}
            {CASE_NAV.map((n) => {
              const on = n.id === screen;
              return navBtn(n, on, { h: 36, fs: 13.5, fw: on ? 700 : 500, iconSize: 19, iconColor: c.ink2, bg: on ? c.bg : 'transparent', hoverBg: on ? c.bg : c.hover });
            })}
            <div style={{ flex: 1 }} />
            {footBtn('Sign out', 'logout', () => {
              api.post('/auth/logout').catch(() => {});
              setToken(null); setAuthed(false); setScreen('dashboard'); setCollapsed(false);
              setNav({ caseId: null, evidenceId: null, jobId: null });
            }, 'Sign out')}
            {footBtn('Collapse', expanded ? 'left_panel_close' : 'left_panel_open', () => setCollapsed((v) => !v), 'Collapse sidebar')}
          </aside>

          <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
            <header style={{ height: 64, flex: 'none', borderBottom: `1px solid ${c.border}`, display: 'flex', alignItems: 'center', gap: 12, padding: '0 20px 0 24px', background: c.bg }}>
              <div style={{ flex: 1, minWidth: 200, maxWidth: 440, height: 40, borderRadius: 999, background: c.surface, border: `1px solid ${c.border}`, display: 'flex', alignItems: 'center', gap: 8, padding: '0 8px 0 14px' }}>
                <Icon name="search" size={19} style={{ color: c.ink2 }} />
                <input ref={searchRef} type="search" aria-label="Search cases" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') go('cases'); if (e.key === 'Escape') setQuery(''); }} placeholder="Search cases, evidence, hashes, finding IDs" style={{ flex: 1, minWidth: 0, border: 'none', outline: 'none', background: 'transparent', fontFamily: 'inherit', fontSize: 13.5, color: c.ink }} />
                <span style={{ fontFamily: MONO, fontSize: 11, color: c.ink2, border: `1px solid ${c.border}`, background: c.bg, borderRadius: 6, padding: '2px 6px' }}>⌘K</span>
              </div>
              <div style={{ flex: 1 }} />
              <div title={`${privacy.badge} · ${privacy.detail}`} style={{ display: 'flex', alignItems: 'center', gap: 8, height: 32, padding: '0 12px', borderRadius: 999, border: `1px solid ${c.border}`, fontSize: 12.5, fontWeight: 600, color: c.ink, whiteSpace: 'nowrap' }}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#3E9B5F' }} />
                {wideBar
                  ? <span>{privacy.badge} · <span style={{ color: c.ink2, fontWeight: 500 }}>{privacy.detail}</span></span>
                  : <span>{privacy.short}</span>}
              </div>
              <button onClick={toggleTheme} title="Switch theme" {...hover({ bg: c.surface }, { width: 40, height: 40, flex: 'none', borderRadius: '50%', border: `1px solid ${c.border}`, background: c.bg, color: c.ink, cursor: 'pointer' })}>
                <Icon name={theme === 'dark' ? 'light_mode' : 'dark_mode'} />
              </button>
              <button
                onClick={() => go('newcase', { draftId: null })}
                {...hover({ bg: ownPrimary ? c.surface : YELLOW_HOVER }, { display: 'inline-flex', alignItems: 'center', gap: 6, height: 40, padding: '0 18px', borderRadius: 999, background: ownPrimary ? c.bg : YELLOW, border: `1px solid ${ownPrimary ? c.border : YELLOW}`, color: ownPrimary ? c.ink : '#111111', fontFamily: 'inherit', fontSize: 14, fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap' })}
              >
                <Icon name="add" size={19} />New case
              </button>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, paddingLeft: 6 }}>
                <div style={{ width: 36, height: 36, borderRadius: '50%', background: c.hero, color: YELLOW, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700 }}>{initials || '·'}</div>
                {wideBar && (
                  <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.2, whiteSpace: 'nowrap' }}>
                    <span style={{ fontSize: 11, color: c.ink2, fontWeight: 600 }}>Investigator</span>
                    <span style={{ fontSize: 13.5, fontWeight: 700 }}>{investigator}</span>
                  </div>
                )}
              </div>
            </header>

            {/* All screens stay mounted (hidden with display:none) so their local state survives navigation. */}
            <main ref={mainRef} style={{ flex: 1, minHeight: 0, overflow: 'auto', background: c.bg }}>
              <div style={shown('dashboard')}><Dashboard go={go} active={is('dashboard')} investigator={investigator} /></div>
              <div style={shown('cases')}><Cases go={go} active={is('cases')} query={query} onClearQuery={() => setQuery('')} /></div>
              <div style={shown('library')}><EvidenceLibrary go={go} active={is('library')} /></div>
              <div style={shown('validation')}><Validation active={is('validation')} /></div>
              <div style={shown('settings')}><Settings active={is('settings')} onSaved={() => setDataVersion((v) => v + 1)} /></div>
              <div style={shown('newcase')}><NewCase go={go} active={is('newcase')} investigator={investigator} draftId={nav.draftId} /></div>
              <div style={shown('analysis')}><Analysis go={go} active={is('analysis')} caseId={nav.caseId} jobId={nav.jobId} /></div>
              <div style={shown('workspace')}><CaseWorkspace go={go} active={is('workspace')} compact={tablet} caseId={nav.caseId} /></div>
              <div style={shown('image')}><ImageViewer go={go} active={is('image')} caseId={nav.caseId} evidenceId={nav.evidenceId} /></div>
              <div style={shown('audio')}><AudioViewer go={go} active={is('audio')} caseId={nav.caseId} evidenceId={nav.evidenceId} /></div>
              <div style={shown('text')}><TextViewer go={go} active={is('text')} caseId={nav.caseId} evidenceId={nav.evidenceId} /></div>
              <div style={shown('report')}><ReportPreview go={go} active={is('report')} caseId={nav.caseId} /></div>
            </main>
          </div>
        </div>
      </div>
    </div>
  );
}
