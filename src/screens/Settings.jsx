import { c, MONO, Icon, eyebrow, h1, page, Muted } from '../ui.jsx';
import { api, useApi, fmtBytes, shortHash } from '../api/client.js';

const ICONS = { exif: 'data_object', ela: 'image', noise: 'grain', jpeg_ghost: 'layers', copy_move: 'content_copy',
  av_metadata: 'info', frames: 'burst_mode', frame_dupes: 'filter_none', optical_flow: 'movie', face_flicker: 'face',
  frame_forensics: 'center_focus_strong', noise_floor: 'graphic_eq', band_limit: 'equalizer', prosody: 'record_voice_over',
  transcript: 'subtitles', claims: 'notes', consistency: 'join_inner' };

function privacyRows(hosted) {
  const dot = (color) => <span style={{ width: 7, height: 7, borderRadius: '50%', background: color }} />;
  return [
    ['Network access', <span key="n" style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600 }}>{dot('#3E9B5F')}
      {hosted ? 'Analysis runs on the TruthLens server and never calls outside services.' : 'Off. All analysis runs on this device.'}</span>],
    ['Telemetry', <span key="t" style={{ fontWeight: 600 }}>Off</span>],
    ['Evidence vault', null],
    ['Who can see your cases', <span key="w" style={{ fontWeight: 600 }}>{hosted ? 'Only your account' : 'Everyone using this device'}</span>],
    ['Cost per analysis', <span key="c" style={{ fontWeight: 600 }}>₹0</span>],
  ];
}

export default function Settings({ active, onSaved }) {
  const st = useApi(active ? '/settings' : null);
  const toggle = (key, enabled) => {
    st.setData((d) => ({ ...d, analyzers: d.analyzers.map((a) => (a.key === key ? { ...a, enabled } : a)) }));
    api.put('/settings', { analyzers: { [key]: enabled } }).then((d) => { st.setData(d); onSaved?.(); }, () => st.reload());
  };
  const vault = st.data ? <span key="v" style={{ fontFamily: MONO, fontSize: 12.5 }}>{st.data.vault.path} · {fmtBytes(st.data.vault.bytes)} · originals read-only</span> : null;

  return (
    <div style={{ ...page, maxWidth: 960 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={eyebrow}>Settings · this device</div>
        <h1 style={h1}>Settings</h1>
      </div>
      <section style={{ border: `1px solid ${c.border}`, borderRadius: 16, overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', background: c.surface, borderBottom: `1px solid ${c.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 16, fontWeight: 800 }}>Analyzers</span>
          <span style={{ fontFamily: MONO, fontSize: 11.5, color: c.ink2 }}>models.lock {shortHash(st.data?.models_lock)}</span>
        </div>
        {st.error && <div style={{ padding: '14px 20px' }}><Muted>Could not load settings: {st.error.message}</Muted></div>}
        {(st.data?.analyzers || []).map(({ key, name, desc, version: ver, enabled: on, available }) => {
          const icon = ICONS[key] || 'tune';
          return (
            <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '14px 20px', borderBottom: `1px solid ${c.line}` }}>
              <Icon name={icon} style={{ color: c.ink2 }} />
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
                <span style={{ fontSize: 14, fontWeight: 700 }}>{name}</span>
                <span style={{ fontSize: 12.5, color: c.ink2 }}>{desc}{available ? '' : ' · not installed on this device'}</span>
              </div>
              <span style={{ fontFamily: MONO, fontSize: 11.5, color: c.ink2 }}>{ver}</span>
              <button
                role="switch"
                aria-checked={on}
                aria-label={name}
                onClick={() => toggle(key, !on)}
                style={{ width: 44, height: 26, borderRadius: 999, border: 'none', padding: 3, background: on ? c.ink : 'var(--tl-border2,#D5D5CF)', cursor: 'pointer', display: 'flex', justifyContent: on ? 'flex-end' : 'flex-start' }}
              >
                <span style={{ width: 20, height: 20, borderRadius: '50%', background: c.bg, boxShadow: '0 1px 2px rgba(0,0,0,.2)' }} />
              </button>
            </div>
          );
        })}
      </section>
      <section style={{ border: `1px solid ${c.border}`, borderRadius: 16, padding: '18px 20px', display: 'grid', gridTemplateColumns: '200px 1fr', gap: '12px 20px', fontSize: 14 }}>
        <span style={{ gridColumn: '1 / -1', fontSize: 16, fontWeight: 800 }}>Privacy and storage</span>
        {privacyRows(st.data?.mode === 'hosted').flatMap(([k, v]) => [<span key={k} style={{ color: c.ink2 }}>{k}</span>, v || vault])}
      </section>
    </div>
  );
}
