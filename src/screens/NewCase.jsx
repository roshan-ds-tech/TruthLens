import { c, YELLOW, MONO, Icon, eyebrow, h1, page, PrimaryButton, SecondaryButton } from '../ui.jsx';

const KINDS = [{ icon: 'image', label: 'Image' }, { icon: 'movie', label: 'Video' }, { icon: 'graphic_eq', label: 'Audio' }, { icon: 'notes', label: 'Text' }];

const FILES = [
  { icon: 'movie', name: 'minister_holiday_clip.mp4', meta: 'Video · 18.4 MB · 00:42 · 1280×720', sha: '9f2c41a7…e81b' },
  { icon: 'image', name: 'podium_photo.jpg', meta: 'Image · 2.1 MB · 1280×720', sha: '3b7e0d19…a4c2' },
];

const field = { border: `1px solid ${c.border}`, borderRadius: 12, fontFamily: 'inherit', fontSize: 14, color: c.ink, outline: 'none', background: c.bg };
const label = { fontSize: 12.5, fontWeight: 700 };

export default function NewCase({ go }) {
  return (
    <div style={{ ...page, maxWidth: 1100 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={eyebrow}>New case · <span style={{ fontFamily: MONO }}>C-0007</span> · Draft</div>
        <h1 style={h1}>Open a new case</h1>
        <p style={{ margin: 0, fontSize: 14.5, color: c.ink2 }}>Add the evidence you received. Files are hashed on arrival and the originals are never modified.</p>
      </div>

      <section style={{ border: `1px solid ${c.border}`, borderRadius: 16, padding: 20, display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 16 }}>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={label}>Case title</span>
          <input defaultValue="Viral clip: minister announces holiday" style={{ ...field, height: 42, padding: '0 14px' }} />
        </label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={label}>Investigator</span>
          <div style={{ height: 42, border: `1px solid ${c.border}`, borderRadius: 12, padding: '0 8px', display: 'flex', alignItems: 'center', gap: 10, fontSize: 14 }}>
            <span style={{ width: 28, height: 28, borderRadius: '50%', background: c.hero, color: YELLOW, fontSize: 11, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>PS</span>
            Priya S.
            <span style={{ flex: 1 }} />
            <Icon name="expand_more" style={{ color: c.ink2 }} />
          </div>
        </div>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 6, gridColumn: '1 / -1' }}>
          <span style={label}>Description</span>
          <textarea
            defaultValue="Clip forwarded on WhatsApp on 12 Nov 2026 claiming the minister announced a three-day state holiday. A still photo of the podium was shared with it. Requested by the newsroom fact-check desk."
            style={{ ...field, minHeight: 72, padding: '12px 14px', lineHeight: 1.5, resize: 'vertical' }}
          />
        </label>
      </section>

      <section style={{ border: `1.5px dashed ${c.border2}`, borderRadius: 16, background: c.surface, padding: '36px 24px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, textAlign: 'center' }}>
        <span style={{ width: 52, height: 52, borderRadius: 14, background: c.bg, border: `1px solid ${c.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name="upload" size={26} /></span>
        <span style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.02em' }}>
          Drop evidence here, or <span style={{ textDecoration: 'underline', textDecorationColor: YELLOW, textDecorationThickness: 2, textUnderlineOffset: 3 }}>browse files</span>
        </span>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 6 }}>
          {KINDS.map((k) => (
            <span key={k.label} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, height: 28, padding: '0 12px', borderRadius: 999, background: c.bg, border: `1px solid ${c.border}`, fontSize: 12.5, fontWeight: 600 }}>
              <Icon name={k.icon} size={16} />{k.label}
            </span>
          ))}
        </div>
        <span style={{ fontFamily: MONO, fontSize: 12, color: c.ink2 }}>Video ≤ 60 s, 720p · Audio ≤ 2 min · Image ≤ 20 MB</span>
      </section>

      <section style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <span style={eyebrow}>Uploaded evidence · 2</span>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(320px,1fr))', gap: 12 }}>
          {FILES.map((f) => (
            <div key={f.name} style={{ border: `1px solid ${c.border}`, borderRadius: 14, padding: 16, display: 'flex', flexDirection: 'column', gap: 12, boxShadow: '0 1px 2px rgba(17,17,17,.04)' }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                <span style={{ width: 40, height: 40, flex: 'none', borderRadius: 10, background: c.surface, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name={f.icon} size={21} /></span>
                <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <span style={{ fontSize: 14.5, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{f.name}</span>
                  <span style={{ fontSize: 12.5, color: c.ink2 }}>{f.meta}</span>
                </div>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: 24, padding: '0 10px', borderRadius: 999, background: c.surface, border: `1px solid ${c.border}`, fontSize: 12, fontWeight: 600 }}>
                  <Icon name="check_circle" size={15} style={{ color: '#3E9B5F' }} />Ready
                </span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 8, paddingTop: 10, borderTop: `1px solid ${c.line}` }}>
                <span style={{ fontFamily: MONO, fontSize: 12 }}>sha256 {f.sha}</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12.5, color: c.ink2 }}>
                  <Icon name="lock" size={16} style={{ color: c.ink }} />Original preserved (read-only)
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section style={{ border: `1px solid ${c.border}`, borderRadius: 16, padding: 20, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 15, fontWeight: 800 }}>Paste caption or claim</span>
          <span style={{ fontSize: 12.5, color: c.ink2 }}>Checked against dates, names and places in the other evidence</span>
        </div>
        <textarea
          defaultValue="BREAKING: Minister announces 3-day state holiday from tomorrow. Schools and offices closed. Forward to all groups. — 12 Nov 2026"
          style={{ ...field, minHeight: 84, padding: '12px 14px', lineHeight: 1.5, resize: 'vertical', background: c.surface }}
        />
        <span style={{ fontFamily: MONO, fontSize: 11.5, color: c.ink2 }}>Source: WhatsApp forward · received 12 Nov 2026 21:40 · 214 characters</span>
      </section>

      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 14, paddingTop: 4 }}>
        <span style={{ fontSize: 13, color: c.ink2 }}>Runs on this device. Estimated time 40–60 s.</span>
        <div style={{ display: 'flex', gap: 10 }}>
          <SecondaryButton style={{ height: 42, padding: '0 18px' }}>Save draft</SecondaryButton>
          <PrimaryButton onClick={() => go('analysis')}>Start analysis<Icon name="arrow_forward" size={19} /></PrimaryButton>
        </div>
      </div>
    </div>
  );
}
