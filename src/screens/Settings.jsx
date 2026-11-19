import { useState } from 'react';
import { c, MONO, Icon, eyebrow, h1, page } from '../ui.jsx';

const ANALYZERS = [
  ['image', 'Error level analysis', 'JPEG recompression differences', 'ela 1.2.0'],
  ['grain', 'Noise map', 'Sensor noise consistency across regions', 'noiseprint 0.8.3'],
  ['content_copy', 'Copy-move', 'Duplicated regions within one image', 'cmfd 0.5.1'],
  ['movie', 'Optical flow', 'Motion breaks between frames', 'flow 2.1.0'],
  ['graphic_eq', 'Noise floor and spectrum', 'Splice and level steps in audio', 'audiofx 0.6.4'],
  ['subtitles', 'Transcript', 'Word-level speech to text', 'whisper-small 2024.3'],
  ['join_inner', 'Lip-sync correlation', 'Mouth movement vs speech energy', 'syncnet 0.3.2'],
];

const PRIVACY = [
  ['Network access', <span key="n" style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600 }}><span style={{ width: 7, height: 7, borderRadius: '50%', background: '#3E9B5F' }} />Off. All analysis runs on this device.</span>],
  ['Telemetry', <span key="t" style={{ fontWeight: 600 }}>Off</span>],
  ['Evidence vault', <span key="v" style={{ fontFamily: MONO, fontSize: 12.5 }}>~/TruthLens/vault · 2.3 GB · originals read-only</span>],
  ['Cost per analysis', <span key="c" style={{ fontWeight: 600 }}>₹0</span>],
];

export default function Settings() {
  const [off, setOff] = useState({});

  return (
    <div style={{ ...page, maxWidth: 960 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={eyebrow}>Settings · this device</div>
        <h1 style={h1}>Settings</h1>
      </div>
      <section style={{ border: `1px solid ${c.border}`, borderRadius: 16, overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', background: c.surface, borderBottom: `1px solid ${c.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 16, fontWeight: 800 }}>Analyzers</span>
          <span style={{ fontFamily: MONO, fontSize: 11.5, color: c.ink2 }}>models.lock e0b2…9c14</span>
        </div>
        {ANALYZERS.map(([icon, name, desc, ver]) => {
          const on = !off[name];
          return (
            <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '14px 20px', borderBottom: `1px solid ${c.line}` }}>
              <Icon name={icon} style={{ color: c.ink2 }} />
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
                <span style={{ fontSize: 14, fontWeight: 700 }}>{name}</span>
                <span style={{ fontSize: 12.5, color: c.ink2 }}>{desc}</span>
              </div>
              <span style={{ fontFamily: MONO, fontSize: 11.5, color: c.ink2 }}>{ver}</span>
              <button
                role="switch"
                aria-checked={on}
                aria-label={name}
                onClick={() => setOff((s) => ({ ...s, [name]: on }))}
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
        {PRIVACY.flatMap(([k, v]) => [<span key={k} style={{ color: c.ink2 }}>{k}</span>, v])}
      </section>
    </div>
  );
}
