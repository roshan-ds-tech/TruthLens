import { useState } from 'react';
import { c, VERDICTS, MONO, Icon, hover, VerdictPill, chipStyle, eyebrow, h1, page } from '../ui.jsx';

const TYPE_ICON = { video: 'movie', image: 'image', audio: 'graphic_eq', text: 'notes' };

const ITEMS = [
  ['minister_holiday_clip.mp4', 'C-0007', 'video', '00:42 · 18.4 MB', 'strong', '9f2c41a7…e81b', 'workspace'],
  ['podium_photo.jpg', 'C-0007', 'image', '1280×720 · 2.1 MB', 'ind', '3b7e0d19…a4c2', 'image'],
  ['Audio track (from clip)', 'C-0007', 'audio', '00:42 · 48 kHz', 'strong', '5d81e0c2…07af', 'audio'],
  ['Caption · WhatsApp forward', 'C-0007', 'text', '214 characters', 'ind', 'c41d9a3e…5f10', 'workspace'],
  ['chennai_flood_post.jpg', 'C-0006', 'image', '1080×1350 · 0.9 MB', 'ind', '71ab3c08…92d4', 'image'],
  ['bank_manager_note.opus', 'C-0005', 'audio', '01:12 · 16 kHz', 'inc', 'e4c90b2f…6a1e', 'audio'],
  ['campus_fest_poster.png', 'C-0004', 'image', '2480×3508 · 6.4 MB', 'none', '0d6f2e91…bb37', 'image'],
  ['review_unboxing.mp4', 'C-0003', 'video', '00:58 · 24.0 MB', 'review', 'a83e57d0…1f2c', 'workspace'],
  ['toll_plaza_cam4.jpg', 'C-0008', 'image', '1920×1080 · 1.7 MB', 'review', '6c2b8f14…d093', 'image'],
  ['donation_screenshot.png', 'C-0002', 'image', '1170×2532 · 1.1 MB', 'none', 'b19a6d72…44e8', 'image'],
  ['rally_speech.m4a', 'C-0001', 'audio', '01:54 · 44.1 kHz', 'inc', '2f7d0c3a…c5b1', 'audio'],
  ['flood_post_caption.txt', 'C-0006', 'text', '388 characters', 'ind', '8e0f4b26…7c3d', 'workspace'],
].map(([name, cs, type, meta, v, sha, dest]) => ({ name, cs, type, meta, v, sha, dest }));

const FILTERS = [['all', 'All', 'apps'], ['image', 'Images', 'image'], ['video', 'Video', 'movie'], ['audio', 'Audio', 'graphic_eq'], ['text', 'Text', 'notes']];

export default function EvidenceLibrary({ go }) {
  const [f, setF] = useState('all');
  const items = ITEMS.filter((i) => f === 'all' || i.type === f);

  return (
    <div style={page}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={eyebrow}>Evidence library · 48 items · 2.3 GB on this device</div>
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
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(230px,1fr))', gap: 14 }}>
        {items.map((it) => (
          <button key={it.name} onClick={() => go(it.dest)} {...hover({ bc: c.ink }, { textAlign: 'left', display: 'flex', flexDirection: 'column', border: `1px solid ${c.border}`, borderRadius: 14, overflow: 'hidden', background: c.bg, fontFamily: 'inherit', color: c.ink, cursor: 'pointer', padding: 0 })}>
            <div style={{ aspectRatio: '16/10', width: '100%', background: 'repeating-linear-gradient(135deg,#F2F2EE 0 10px,#F7F7F5 10px 20px)', position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ fontFamily: MONO, fontSize: 10.5, color: '#8A8A85' }}>{it.type} preview</span>
              <span style={{ position: 'absolute', left: 10, top: 10, width: 28, height: 28, borderRadius: 8, background: c.bg, border: `1px solid ${c.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name={TYPE_ICON[it.type]} size={17} /></span>
            </div>
            <div style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 6, width: '100%' }}>
              <span style={{ fontSize: 13.5, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{it.name}</span>
              <span style={{ fontSize: 12, color: c.ink2 }}><span style={{ fontFamily: MONO }}>{it.cs}</span> · {it.meta}</span>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6 }}>
                <VerdictPill dot={VERDICTS[it.v][1]} label={VERDICTS[it.v][0]} h={22} fs={11.5} pad={9} dotSize={6} />
                <span style={{ fontFamily: MONO, fontSize: 10.5, color: c.ink2 }}>{it.sha}</span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
