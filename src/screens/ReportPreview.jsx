import { c, YELLOW, MONO, Icon, eyebrow, fmtRange, preventThen, PrimaryButton, SecondaryButton } from '../ui.jsx';

// The report pages are print documents: they stay white-on-ink in both themes.
const V = { strong: ['Strong indicators', '#D64545'], ind: ['Indicators', '#E8A33D'], inc: ['Inconclusive', '#8A8A85'] };

const EVIDENCE = [
  { name: 'minister_holiday_clip.mp4', type: 'Video', size: '18.4 MB', sha: '9f2c41a7…e81b' },
  { name: 'Audio track (derived)', type: 'Audio', size: '4.0 MB', sha: '5d81e0c2…07af' },
  { name: 'podium_photo.jpg', type: 'Image', size: '2.1 MB', sha: '3b7e0d19…a4c2' },
  { name: 'Caption · WhatsApp forward', type: 'Text', size: '214 chars', sha: 'c41d9a3e…5f10' },
];

const FINDINGS = [
  ['F-VID-002', 'Optical-flow discontinuity', '00:14.0 · frames 420–423', 0.64, 0.81, 'strong', 'accepted', 'frame 420'],
  ['F-AUD-001', 'Noise-floor step (possible splice)', '00:14.2 · +9 dB', 0.70, 0.86, 'strong', 'accepted', 'spectrogram 14.2 s'],
  ['F-IMG-003', 'Error level inconsistency', 'podium region', 0.52, 0.71, 'ind', 'open', 'ELA crop'],
  ['F-TXT-001', 'Date conflict', 'caption vs EXIF', 0.80, 0.94, 'ind', 'accepted', 'EXIF table'],
  ['F-XM-001', 'Lip-sync weak correlation', '00:14.0–00:19.0', 0.40, 0.62, 'inc', 'open', 'mouth region'],
  ['F-IMG-004', 'Copy-move match', 'banner logo', 0.38, 0.55, 'inc', 'rejected', 'banner crop'],
];

const RULES = [
  { id: 'R-03', name: 'Audio splice within 0.5 s of a motion break', links: 'F-AUD-001 ↔ F-VID-002 · Δ 0.2 s', tag: 'Supports' },
  { id: 'R-07', name: 'Lip-sync drop overlaps a flagged segment', links: 'F-XM-001 ↔ F-VID-002, F-AUD-001', tag: 'Supports (weak)' },
  { id: 'R-11', name: 'Claimed date differs from capture metadata', links: 'F-TXT-001 ↔ F-IMG-003', tag: 'Supports' },
  { id: 'R-14', name: 'Error-level pattern matches platform recompression', links: 'F-IMG-003 ↔ WhatsApp JPEG q≈82', tag: 'Conflicts' },
];

const DECISIONS = [
  { id: 'F-AUD-001', dec: 'Accepted', time: '21:48:33', note: 'Step is audible on headphones.' },
  { id: 'F-VID-002', dec: 'Accepted', time: '21:49:02', note: 'Camera is on a tripod; no reason for motion break.' },
  { id: 'F-TXT-001', dec: 'Accepted', time: '21:49:40', note: 'Earliest copy of photo found in a 2024 news post.' },
  { id: 'F-IMG-004', dec: 'Rejected', time: '21:50:12', note: 'Logo repeats on the printed banner.' },
  { id: 'F-IMG-003', dec: 'Open', time: '—', note: '—' },
];

const LIMITATIONS = [
  'Confidence ranges describe how strongly analyzers agree. They are not the probability that the content was edited.',
  '720p input limits face-region and lip-sync measurements; F-XM-001 is inconclusive for this reason.',
  'Social-platform recompression can produce error-level patterns similar to editing (rule R-14).',
  'Analyzers were validated on a self-made seeded test set only. This is not a general accuracy claim.',
  'The report does not establish who created or altered the content.',
];

const mono = { fontFamily: MONO };
const paper = { width: 794, maxWidth: '100%', minHeight: 1123, background: '#fff', color: '#111', boxShadow: '0 1px 3px rgba(17,17,17,.08),0 12px 40px rgba(17,17,17,.06)', padding: '56px 60px 44px', display: 'flex', flexDirection: 'column', gap: 26, fontSize: 12.5, lineHeight: 1.5 };
const section = { display: 'flex', flexDirection: 'column', gap: 8 };
const label = { fontSize: 10, fontWeight: 700, letterSpacing: '.12em', textTransform: 'uppercase', color: '#5F5F5A' };
const tableHead = { display: 'grid', gap: 10, padding: '8px 12px', background: '#F7F7F5', fontSize: 10, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: '#5F5F5A' };
const tableRow = { display: 'grid', gap: 10, padding: '8px 12px', borderTop: '1px solid #EFEFEB' };

const EV_COLS = '1.6fr .7fr .8fr 1.3fr';
const DEC_COLS = '90px 80px 110px 1fr';

export default function ReportPreview({ go }) {
  return (
    <div style={{ color: c.ink, background: c.surface, minHeight: '100%' }}>
      <div style={{ padding: '28px 40px 20px', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16, background: c.bg, borderBottom: `1px solid ${c.border}` }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <a href="#" onClick={preventThen(() => go('workspace'))} style={{ fontSize: 13, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 4, alignSelf: 'flex-start', textDecoration: 'none' }}><Icon name="arrow_back" size={18} />C-0007 workspace</a>
          <div style={eyebrow}>Report · <span style={mono}>C-0007</span> · Draft 2 · A4 · 2 pages</div>
          <h1 style={{ margin: 0, fontSize: 34, lineHeight: 1.1, fontWeight: 800, letterSpacing: '-0.035em' }}>Forensic report preview</h1>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <SecondaryButton><Icon name="data_object" size={19} />Export JSON</SecondaryButton>
          <PrimaryButton style={{ height: 40, padding: '0 18px' }}>Download PDF<Icon name="arrow_forward" size={19} /></PrimaryButton>
        </div>
      </div>

      <div style={{ padding: '32px 24px 64px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 28 }}>
        <article style={paper}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', paddingBottom: 18, borderBottom: '2px solid #111' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 30, height: 30, borderRadius: 8, background: YELLOW, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><div style={{ width: 15, height: 15, borderRadius: '50%', border: '3px solid #111' }} /></div>
              <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15 }}>
                <span style={{ fontSize: 15, fontWeight: 800, letterSpacing: '-0.02em' }}>TruthLens</span>
                <span style={{ fontSize: 10.5, color: '#5F5F5A' }}>Forensic report</span>
              </div>
            </div>
            <div style={{ textAlign: 'right', ...mono, fontSize: 10.5, color: '#5F5F5A', lineHeight: 1.6 }}>C-0007 · draft 2<br />generated 19 Nov 2026 21:51<br />investigator Priya S.</div>
          </div>

          <div style={section}>
            <span style={label}>Summary</span>
            <h2 style={{ margin: 0, fontSize: 24, fontWeight: 800, letterSpacing: '-0.03em', lineHeight: 1.15 }}>Viral clip: minister announces holiday</h2>
            <p style={{ margin: 0, color: '#333', textWrap: 'pretty' }}>A 42-second clip and a still photo were received as a WhatsApp forward on 12 Nov 2026, with a caption claiming a three-day state holiday. Four evidence items were analyzed on-device. Seven findings were produced; three were accepted by the reviewer, one was rejected and three remain open.</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.4fr', gap: 20, padding: '18px 20px', borderRadius: 12, background: '#111', color: '#fff' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <span style={{ ...label, color: YELLOW }}>Verdict</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 18, fontWeight: 800 }}><span style={{ width: 9, height: 9, borderRadius: '50%', background: '#D64545' }} />Strong indicators</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ position: 'relative', flex: 1, height: 6, borderRadius: 999, background: '#333' }}>
                  <div style={{ position: 'absolute', top: 0, bottom: 0, left: '71%', width: '17%', background: YELLOW, borderRadius: 999 }} />
                </div>
                <span style={{ ...mono, fontSize: 11, color: YELLOW }}>0.71–0.88</span>
              </div>
            </div>
            <p style={{ margin: 0, color: '#D8D8D2', fontSize: 12.5 }}><b style={{ color: '#fff' }}>Why:</b> an audio splice at 00:14.2 lines up with a motion break at 00:14.0, and the caption date conflicts with the photo's metadata. The range reflects agreement between analyzers, not a probability of editing.</p>
          </div>

          <div style={section}>
            <span style={label}>Evidence</span>
            <div style={{ border: '1px solid #E8E8E4', borderRadius: 10, overflow: 'hidden' }}>
              <div style={{ ...tableHead, gridTemplateColumns: EV_COLS }}><span>File</span><span>Type</span><span>Size</span><span>SHA-256</span></div>
              {EVIDENCE.map((e) => (
                <div key={e.sha} style={{ ...tableRow, gridTemplateColumns: EV_COLS }}>
                  <span style={{ fontWeight: 600 }}>{e.name}</span><span>{e.type}</span><span>{e.size}</span><span style={{ ...mono, fontSize: 11 }}>{e.sha}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={section}>
            <span style={label}>Findings</span>
            {FINDINGS.map(([id, name, loc, lo, hi, v, decision, thumb]) => (
              <div key={id} style={{ display: 'grid', gridTemplateColumns: '96px 1fr 150px', gap: 14, alignItems: 'center', padding: '10px 0', borderBottom: '1px solid #EFEFEB' }}>
                <div style={{ height: 56, borderRadius: 6, background: 'repeating-linear-gradient(135deg,#EFEFEB 0 6px,#F7F7F5 6px 12px)', display: 'flex', alignItems: 'center', justifyContent: 'center', ...mono, fontSize: 9, color: '#8A8A85', textAlign: 'center' }}>{thumb}</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <span><span style={{ ...mono, fontSize: 11, fontWeight: 600 }}>{id}</span> · <b>{name}</b></span>
                  <span style={{ color: '#5F5F5A' }}>{loc} · <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><span style={{ width: 6, height: 6, borderRadius: '50%', background: V[v][1] }} />{V[v][0]}</span></span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <div style={{ position: 'relative', height: 6, borderRadius: 999, background: '#EFEFEB' }}>
                    <div style={{ position: 'absolute', top: 0, bottom: 0, left: lo * 100 + '%', width: (hi - lo) * 100 + '%', borderRadius: 999, background: v === 'inc' ? '#8A8A85' : '#111' }} />
                  </div>
                  <span style={{ ...mono, fontSize: 10.5, display: 'flex', justifyContent: 'space-between' }}><span>{fmtRange(lo, hi)}</span><span style={{ color: '#5F5F5A' }}>{decision}</span></span>
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 'auto', display: 'flex', justifyContent: 'space-between', ...mono, fontSize: 10, color: '#8A8A85' }}><span>TruthLens 0.9.1 · generated on device</span><span>page 1 / 2</span></div>
        </article>

        <article style={paper}>
          <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 12, borderBottom: '1px solid #E8E8E4', ...mono, fontSize: 10.5, color: '#5F5F5A' }}><span>C-0007 · Viral clip: minister announces holiday</span><span>draft 2</span></div>

          <div style={section}>
            <span style={label}>Correlation summary</span>
            {RULES.map((r) => (
              <div key={r.id} style={{ display: 'grid', gridTemplateColumns: '48px 1fr auto', gap: 12, padding: '8px 0', borderBottom: '1px solid #EFEFEB' }}>
                <span style={{ ...mono, fontSize: 11, fontWeight: 600 }}>{r.id}</span>
                <span><b>{r.name}</b><br /><span style={{ ...mono, fontSize: 10.5, color: '#5F5F5A' }}>{r.links}</span></span>
                <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 999, border: '1px solid #E8E8E4', alignSelf: 'start' }}>{r.tag}</span>
              </div>
            ))}
          </div>

          <div style={section}>
            <span style={label}>Limitations</span>
            <ul style={{ margin: 0, paddingLeft: 18, color: '#333', display: 'flex', flexDirection: 'column', gap: 4 }}>
              {LIMITATIONS.map((l) => <li key={l}>{l}</li>)}
            </ul>
          </div>

          <div style={section}>
            <span style={label}>Reviewer decisions</span>
            <div style={{ border: '1px solid #E8E8E4', borderRadius: 10, overflow: 'hidden' }}>
              <div style={{ ...tableHead, gridTemplateColumns: DEC_COLS }}><span>Finding</span><span>Decision</span><span>Time</span><span>Note</span></div>
              {DECISIONS.map((d) => (
                <div key={d.id} style={{ ...tableRow, gridTemplateColumns: DEC_COLS }}>
                  <span style={{ ...mono, fontSize: 11 }}>{d.id}</span><span style={{ fontWeight: 700 }}>{d.dec}</span><span style={{ ...mono, fontSize: 11, color: '#5F5F5A' }}>{d.time}</span><span style={{ color: '#333' }}>{d.note}</span>
                </div>
              ))}
            </div>
            <span style={{ color: '#5F5F5A' }}>Reviewed by Priya S. Open findings are listed but carry no reviewer decision.</span>
          </div>

          <div style={section}>
            <span style={label}>Rerun command</span>
            <div style={{ background: '#F7F7F5', border: '1px solid #E8E8E4', borderRadius: 10, padding: '12px 14px', ...mono, fontSize: 11, lineHeight: 1.6, wordBreak: 'break-all' }}>truthlens analyze --case C-0007 --run 2 --vfr --seed 7 --models models.lock@e0b29c14 --evidence 9f2c41a7…e81b 3b7e0d19…a4c2 c41d9a3e…5f10</div>
            <span style={{ color: '#5F5F5A' }}>Running this command on the same files and model lock reproduces these findings.</span>
          </div>

          <div style={{ marginTop: 'auto', paddingTop: 14, borderTop: '2px solid #111', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 8, ...mono, fontSize: 10.5 }}>
            <span>report sha256 4ae09c3b…7d21</span><span style={{ color: '#8A8A85' }}>chain of custody: 9 entries · page 2 / 2</span>
          </div>
        </article>
      </div>
    </div>
  );
}
