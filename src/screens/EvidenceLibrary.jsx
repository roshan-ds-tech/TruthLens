import { useState } from 'react';
import { c, VERDICTS, MONO, Icon, hover, VerdictPill, chipStyle, eyebrow, h1, page, Muted } from '../ui.jsx';
import { useApi, fmtBytes } from '../api/client.js';
import { AuthImg, EvidencePreview } from '../api/media.jsx';

const TYPE_ICON = { video: 'movie', image: 'image', audio: 'graphic_eq', text: 'notes' };

const FILTERS = [['all', 'All', 'apps'], ['image', 'Images', 'image'], ['video', 'Video', 'movie'], ['audio', 'Audio', 'graphic_eq'], ['text', 'Text', 'notes']];

function Thumb({ it }) {
  const [failed, setFailed] = useState(false);
  if (['audio', 'text'].includes(it.kind)) return <EvidencePreview ev={it} lines={3} />;
  if (failed) return <span style={{ fontFamily: MONO, fontSize: 10.5, color: '#8A8A85' }}>{it.kind} preview</span>;
  return <AuthImg path={it.thumb_url} alt="" onError={() => setFailed(true)} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }} />;
}

const DEST = { image: 'image', audio: 'audio' };

export default function EvidenceLibrary({ go, active }) {
  const [f, setF] = useState('all');
  const lib = useApi(active ? '/evidence' : null);
  const all = lib.data?.items || [];
  const items = all.filter((i) => f === 'all' || i.kind === f);

  return (
    <div style={page}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={eyebrow}>Evidence library · {lib.data ? `${lib.data.count} items · ${fmtBytes(lib.data.total_bytes)} on this device` : 'loading'}</div>
        <h1 style={h1}>Evidence Library</h1>
        <p style={{ margin: 0, fontSize: 14.5, color: c.ink2 }}>Every original is stored read-only and identified by its SHA-256 hash.</p>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {FILTERS.map(([k, label, icon]) => (
          <button key={k} onClick={() => setF(k)} style={{ ...chipStyle(f === k), gap: 6 }}>
            <Icon name={icon} size={17} />{label}
          </button>
        ))}
      </div>
      {lib.error && <Muted>Could not load evidence: {lib.error.message}</Muted>}
      {lib.data && !items.length && <Muted>{all.length ? 'No evidence of this type.' : 'No evidence yet. Add files from New case.'}</Muted>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(230px,1fr))', gap: 14 }}>
        {items.map((it) => (
          <button key={it.id} onClick={() => go(DEST[it.kind] || 'workspace', { caseId: it.case_id, evidenceId: it.id })} {...hover({ bc: c.ink }, { textAlign: 'left', display: 'flex', flexDirection: 'column', border: `1px solid ${c.border}`, borderRadius: 14, overflow: 'hidden', background: c.bg, fontFamily: 'inherit', color: c.ink, cursor: 'pointer', padding: 0 })}>
            <div style={{ aspectRatio: '16/10', width: '100%', background: 'repeating-linear-gradient(135deg,#F2F2EE 0 10px,#F7F7F5 10px 20px)', position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Thumb it={it} />
              <span style={{ position: 'absolute', left: 10, top: 10, width: 28, height: 28, borderRadius: 8, background: c.bg, border: `1px solid ${c.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name={TYPE_ICON[it.kind]} size={17} /></span>
            </div>
            <div style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 6, width: '100%' }}>
              <span style={{ fontSize: 13.5, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{it.display_name}</span>
              <span style={{ fontSize: 12, color: c.ink2 }}><span style={{ fontFamily: MONO }}>{it.case_id}</span> · {it.meta_label.split(' · ').slice(1).join(' · ')}</span>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6 }}>
                <VerdictPill dot={VERDICTS[it.verdict?.key || 'review'][1]} label={it.verdict?.label || 'Not analyzed'} h={22} fs={11.5} pad={9} dotSize={6} />
                <span style={{ fontFamily: MONO, fontSize: 10.5, color: c.ink2 }}>{it.sha_short}</span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
