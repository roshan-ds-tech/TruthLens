import { useState } from 'react';
import { c, YELLOW, YELLOW_HOVER, MONO, Icon, Logo, hover, Muted } from '../ui.jsx';
import { api, setToken, useServerMode, PRIVACY } from '../api/client.js';
import HomePreview from './HomePreview.jsx';

const KINDS = [{ icon: 'image', label: 'Image' }, { icon: 'movie', label: 'Video' }, { icon: 'graphic_eq', label: 'Audio' }, { icon: 'notes', label: 'Text' }];

const POINTS = [
  { icon: 'lock', title: null, text: null },   // wording depends on local vs hosted mode (PRIVACY)
  { icon: 'my_location', title: 'Every finding is linked', text: 'Each finding points to its exact region, timestamp or transcript span.' },
  { icon: 'rate_review', title: 'You review, then report', text: 'Accept or reject each finding, then export a reproducible report.' },
];

const input = { height: 42, border: `1px solid ${c.border}`, borderRadius: 12, padding: '0 14px', fontFamily: 'inherit', fontSize: 14, outline: 'none', background: c.bg, color: c.ink };

function Field({ label, ...rest }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <span style={{ fontSize: 12.5, fontWeight: 700 }}>{label}</span>
      <input style={input} required {...rest} />
    </label>
  );
}

export default function Home({ theme, onEnter, onToggleTheme }) {
  const [mode, setMode] = useState(null);
  const privacy = PRIVACY[useServerMode()];
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const su = mode === 'signup';
  const close = () => { setMode(null); setError(''); };
  const field = (k) => ({ value: form[k], onChange: (e) => setForm((f) => ({ ...f, [k]: e.target.value })) });
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const r = su ? await api.post('/auth/signup', form) : await api.post('/auth/login', { email: form.email, password: form.password });
      setToken(r.token);
      setForm({ name: '', email: '', password: '' });
      setMode(null);
      onEnter?.(r.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  const dot = (bg) => <span style={{ width: 10, height: 10, borderRadius: '50%', background: bg }} />;

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', color: c.ink, background: c.bg }}>
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, padding: '20px 40px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Logo lockup size={38} />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, height: 36, padding: '0 14px', borderRadius: 999, border: `1px solid ${c.border}`, fontSize: 12.5, fontWeight: 600 }}>
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#3E9B5F' }} />{privacy.home}
          </div>
          <button onClick={onToggleTheme} title="Switch theme" {...hover({ bg: c.surface }, { width: 36, height: 36, borderRadius: '50%', border: `1px solid ${c.border}`, background: c.bg, color: c.ink, cursor: 'pointer' })}>
            <Icon name={theme === 'dark' ? 'light_mode' : 'dark_mode'} size={19} />
          </button>
        </div>
      </header>

      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '56px 24px 72px', gap: 56 }}>
        <div style={{ maxWidth: 760, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 22, textAlign: 'center' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 6 }}>
            {KINDS.map((k) => (
              <span key={k.label} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: 30, padding: '0 12px', borderRadius: 999, background: c.surface, border: `1px solid ${c.border}`, fontSize: 12.5, fontWeight: 700 }}>
                <Icon name={k.icon} size={16} />{k.label}
              </span>
            ))}
          </div>
          <h1 style={{ margin: 0, fontSize: 58, lineHeight: 1.04, fontWeight: 700, letterSpacing: '-0.025em', textWrap: 'balance' }}>
            Check photos, videos, audio and text for signs of{' '}
            <span style={{ background: `linear-gradient(transparent 62%,${YELLOW} 62%,${YELLOW} 92%,transparent 92%)` }}>manipulation</span>.
          </h1>
          <p style={{ margin: 0, fontSize: 17, lineHeight: 1.55, color: c.ink2, maxWidth: 580, textWrap: 'pretty' }}>
            {privacy.hero} every finding with its exact location and confidence range, and lets you review each one before producing a report.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 10, paddingTop: 6 }}>
            <button onClick={() => setMode('signup')} {...hover({ bg: YELLOW_HOVER }, { display: 'inline-flex', alignItems: 'center', gap: 8, height: 48, padding: '0 24px', borderRadius: 999, background: YELLOW, border: 'none', fontFamily: 'inherit', fontSize: 15, fontWeight: 700, color: '#111111', cursor: 'pointer' })}>
              Sign up<Icon name="arrow_forward" />
            </button>
            <button onClick={() => setMode('login')} {...hover({ bg: c.surface }, { display: 'inline-flex', alignItems: 'center', height: 48, padding: '0 24px', borderRadius: 999, background: c.bg, border: `1px solid ${c.border}`, fontFamily: 'inherit', fontSize: 15, fontWeight: 700, color: c.ink, cursor: 'pointer' })}>
              Log in
            </button>
          </div>
        </div>

        <section style={{ width: '100%', maxWidth: 1040, border: `1px solid ${c.border}`, borderRadius: 20, background: c.surface, padding: 14, boxShadow: '0 24px 60px rgba(17,17,17,.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 6px 12px' }}>
            {dot(c.border)}{dot(c.border)}{dot(c.border)}
            <span style={{ marginLeft: 10, fontSize: 11, fontWeight: 700, letterSpacing: '.12em', textTransform: 'uppercase', color: c.ink2 }}>
              Case · <span style={{ fontFamily: MONO }}>C-0007</span> · Viral clip: minister announces holiday
            </span>
          </div>
          <HomePreview />
        </section>

        <div style={{ width: '100%', maxWidth: 1040, display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 28 }}>
          {POINTS.map((p) => ({ ...p, title: p.title || privacy.pointTitle, text: p.text || privacy.pointText })).map((p) => (
            <div key={p.title} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <span style={{ width: 40, height: 40, borderRadius: 12, background: c.surface, border: `1px solid ${c.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name={p.icon} size={21} /></span>
              <span style={{ fontSize: 16, fontWeight: 700, letterSpacing: '-0.01em' }}>{p.title}</span>
              <span style={{ fontSize: 14, lineHeight: 1.5, color: c.ink2 }}>{p.text}</span>
            </div>
          ))}
        </div>
      </main>

      {mode && (
        <>
          <div onClick={close} style={{ position: 'fixed', inset: 0, background: 'rgba(17,17,17,.4)', zIndex: 50 }} />
          <form
            role="dialog" aria-modal="true" aria-labelledby="tl-auth-title"
            onSubmit={submit} onKeyDown={(e) => { if (e.key === 'Escape') close(); }}
            style={{ position: 'fixed', left: '50%', top: '50%', transform: 'translate(-50%,-50%)', width: 'min(400px,92vw)', background: c.bg, color: c.ink, border: `1px solid ${c.border}`, borderRadius: 16, padding: 28, zIndex: 51, boxShadow: '0 20px 60px rgba(17,17,17,.18)', display: 'flex', flexDirection: 'column', gap: 16 }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.12em', textTransform: 'uppercase', color: c.ink2 }}>{su ? privacy.account : 'Log in'}</span>
                <span id="tl-auth-title" style={{ fontSize: 24, fontWeight: 700, letterSpacing: '-0.018em' }}>{su ? 'Create your account' : 'Welcome back'}</span>
              </div>
              <button type="button" onClick={close} aria-label="Close" style={{ width: 34, height: 34, borderRadius: '50%', border: `1px solid ${c.border}`, background: c.bg, color: c.ink, cursor: 'pointer' }}><Icon name="close" size={19} /></button>
            </div>
            {su && <Field label="Full name" autoComplete="name" autoFocus {...field('name')} />}
            <Field label="Email" type="email" autoComplete="email" autoFocus={!su} {...field('email')} />
            <Field label="Password" type="password" minLength={su ? 8 : undefined} autoComplete={su ? 'new-password' : 'current-password'} {...field('password')} />
            {su && <Muted style={{ fontSize: 12 }}>At least 8 characters.</Muted>}
            {error && <Muted style={{ fontSize: 12.5, color: c.ink }} role="alert">{error}</Muted>}
            <button type="submit" disabled={busy} {...hover({ bg: YELLOW_HOVER }, { opacity: busy ? 0.6 : 1, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8, height: 44, borderRadius: 999, background: YELLOW, border: 'none', fontFamily: 'inherit', fontSize: 14.5, fontWeight: 700, color: '#111111', cursor: 'pointer' })}>
              {busy ? 'Please wait…' : su ? 'Create account' : 'Log in'}<Icon name="arrow_forward" size={19} />
            </button>
            <span style={{ fontSize: 13, color: c.ink2, textAlign: 'center' }}>
              {su ? 'Already have an account?' : 'New to Vero?'}{' '}
              <a href="#" onClick={(e) => { e.preventDefault(); setError(''); setMode(su ? 'login' : 'signup'); }} style={{ fontWeight: 700, color: c.ink }}>{su ? 'Log in' : 'Sign up'}</a>
            </span>
          </form>
        </>
      )}
    </div>
  );
}
