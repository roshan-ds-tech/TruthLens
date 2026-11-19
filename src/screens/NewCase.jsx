import { useEffect, useRef, useState } from 'react';
import { c, YELLOW, MONO, Icon, eyebrow, h1, page, PrimaryButton, SecondaryButton, Muted } from '../ui.jsx';
import { api, useServerMode } from '../api/client.js';

const KINDS = [{ icon: 'image', label: 'Image' }, { icon: 'movie', label: 'Video' }, { icon: 'graphic_eq', label: 'Audio' }, { icon: 'notes', label: 'Text' }];

const ICON = { video: 'movie', image: 'image', audio: 'graphic_eq', text: 'notes' };

const field = { border: `1px solid ${c.border}`, borderRadius: 12, fontFamily: 'inherit', fontSize: 14, color: c.ink, outline: 'none', background: c.bg };
const label = { fontSize: 12.5, fontWeight: 700 };

export default function NewCase({ go, active, caseId, investigator }) {
  const [draftId, setDraftId] = useState(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [caption, setCaption] = useState('');
  const [captionSent, setCaptionSent] = useState('');
  const [files, setFiles] = useState([]);       // uploaded evidence (API objects) and in-flight placeholders
  const [messages, setMessages] = useState([]);  // rejected files, save confirmations, errors
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const input = useRef(null);
  const hosted = useServerMode() === 'hosted';

  // Resume a draft case; any other case opens an empty form.
  useEffect(() => {
    if (!active) return;
    if (!caseId) { reset(); return; }
    api.get(`/cases/${caseId}`).then((cs) => {
      if (cs.status !== 'draft') { if (draftId !== null) reset(); return; }
      setDraftId(cs.id); setTitle(cs.title); setDescription(cs.description);
      setFiles(cs.evidence.filter((e) => e.kind !== 'text' && !e.derived_from));
    }, () => reset());
  }, [active, caseId]); // eslint-disable-line react-hooks/exhaustive-deps

  function reset() {
    setDraftId(null); setTitle(''); setDescription(''); setCaption(''); setCaptionSent(''); setFiles([]); setMessages([]);
  }

  async function ensureCase() {
    if (draftId) {
      await api.patch(`/cases/${draftId}`, { title: title.trim() || 'Untitled case', description });
      return draftId;
    }
    const cs = await api.post('/cases', { title: title.trim() || 'Untitled case', description, investigator });
    setDraftId(cs.id);
    go('newcase', { caseId: cs.id });
    return cs.id;
  }

  async function addFiles(list) {
    const picked = Array.from(list || []);
    if (!picked.length) return;
    setBusy(true);
    try {
      const id = await ensureCase();
      for (const f of picked) {
        const key = `pending-${f.name}-${f.size}`;
        setFiles((fs) => [...fs, { id: key, pending: true, kind: 'image', filename: f.name, meta_label: 'Hashing and sealing…', sha_short: '' }]);
        try {
          const ev = await api.upload(id, f);
          setFiles((fs) => [...fs.filter((x) => x.id !== key && x.id !== ev.id), ev]);
        } catch (e) {
          setFiles((fs) => fs.filter((x) => x.id !== key));
          setMessages((m) => [...m, `${f.name} was not added: ${e.message}`]);
        }
      }
    } catch (e) {
      setMessages((m) => [...m, `Could not create the case: ${e.message}`]);
    } finally {
      setBusy(false);
    }
  }

  async function saveCaption(id) {
    const text = caption.trim();
    if (text && text !== captionSent) {
      await api.addText(id, text, 'Pasted caption or claim');
      setCaptionSent(text);
    }
  }

  async function saveDraft() {
    setBusy(true);
    try {
      const id = await ensureCase();
      await saveCaption(id);
      setMessages((m) => [...m, `Draft ${id} saved.`]);
    } catch (e) {
      setMessages((m) => [...m, `Could not save: ${e.message}`]);
    } finally { setBusy(false); }
  }

  async function start() {
    setBusy(true);
    try {
      const id = await ensureCase();
      await saveCaption(id);
      const job = await api.post(`/cases/${id}/analyze`);
      reset();
      go('analysis', { caseId: id, jobId: job.job_id });
    } catch (e) {
      setMessages((m) => [...m, e.message]);
    } finally { setBusy(false); }
  }

  const evidence = files.filter((f) => f.kind !== 'text');
  return (
    <div style={{ ...page, maxWidth: 1100 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={eyebrow}>New case · <span style={{ fontFamily: MONO }}>{draftId || 'not saved yet'}</span> · Draft</div>
        <h1 style={h1}>Open a new case</h1>
        <p style={{ margin: 0, fontSize: 14.5, color: c.ink2 }}>Add the evidence you received. Files are hashed on arrival and the originals are never modified.</p>
      </div>

      <section style={{ border: `1px solid ${c.border}`, borderRadius: 16, padding: 20, display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 16 }}>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={label}>Case title</span>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Viral clip: minister announces holiday" style={{ ...field, height: 42, padding: '0 14px' }} />
        </label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={label}>Investigator</span>
          <div style={{ height: 42, border: `1px solid ${c.border}`, borderRadius: 12, padding: '0 8px', display: 'flex', alignItems: 'center', gap: 10, fontSize: 14 }}>
            <span style={{ width: 28, height: 28, borderRadius: '50%', background: c.hero, color: YELLOW, fontSize: 11, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{investigator.split(/\s+/).map((w) => w[0]).join('').slice(0, 2).toUpperCase()}</span>
            {investigator}
            <span style={{ flex: 1 }} />
            <Icon name="expand_more" style={{ color: c.ink2 }} />
          </div>
        </div>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 6, gridColumn: '1 / -1' }}>
          <span style={label}>Description</span>
          <textarea
            value={description} onChange={(e) => setDescription(e.target.value)}
            placeholder="Where the evidence came from, when it was received and who asked for the check."
            style={{ ...field, minHeight: 72, padding: '12px 14px', lineHeight: 1.5, resize: 'vertical' }}
          />
        </label>
      </section>

      <section
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); addFiles(e.dataTransfer.files); }}
        style={{ border: `1.5px dashed ${drag ? c.ink : c.border2}`, borderRadius: 16, background: c.surface, padding: '36px 24px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, textAlign: 'center' }}>
        <span style={{ width: 52, height: 52, borderRadius: 14, background: c.bg, border: `1px solid ${c.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name="upload" size={26} /></span>
        <span style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.02em' }}>
          Drop evidence here, or <span onClick={() => input.current?.click()} style={{ cursor: 'pointer', textDecoration: 'underline', textDecorationColor: YELLOW, textDecorationThickness: 2, textUnderlineOffset: 3 }}>browse files</span>
        </span>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 6 }}>
          {KINDS.map((k) => (
            <span key={k.label} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, height: 28, padding: '0 12px', borderRadius: 999, background: c.bg, border: `1px solid ${c.border}`, fontSize: 12.5, fontWeight: 600 }}>
              <Icon name={k.icon} size={16} />{k.label}
            </span>
          ))}
        </div>
        <span style={{ fontFamily: MONO, fontSize: 12, color: c.ink2 }}>Video ≤ 60 s, 720p · Audio ≤ 2 min · Image ≤ 20 MB</span>
        <input ref={input} type="file" multiple hidden accept="image/*,video/*,audio/*,.txt" onChange={(e) => { addFiles(e.target.files); e.target.value = ''; }} />
        {messages.map((m, i) => <Muted key={i} style={{ fontSize: 12.5 }}>{m}</Muted>)}
      </section>

      <section style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <span style={eyebrow}>Uploaded evidence · {evidence.length}</span>
        {!evidence.length && <Muted>Nothing added yet.</Muted>}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(320px,1fr))', gap: 12 }}>
          {evidence.map((f) => (
            <div key={f.id} style={{ border: `1px solid ${c.border}`, borderRadius: 14, padding: 16, display: 'flex', flexDirection: 'column', gap: 12, boxShadow: '0 1px 2px rgba(17,17,17,.04)' }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                <span style={{ width: 40, height: 40, flex: 'none', borderRadius: 10, background: c.surface, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon name={ICON[f.kind] || 'description'} size={21} /></span>
                <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <span style={{ fontSize: 14.5, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{f.filename}</span>
                  <span style={{ fontSize: 12.5, color: c.ink2 }}>{f.meta_label}{f.warnings?.length ? ` · ${f.warnings[0]}` : ''}</span>
                </div>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: 24, padding: '0 10px', borderRadius: 999, background: c.surface, border: `1px solid ${c.border}`, fontSize: 12, fontWeight: 600 }}>
                  <Icon name={f.pending ? 'hourglass_empty' : 'check_circle'} size={15} style={{ color: f.pending ? c.ink2 : '#3E9B5F' }} />{f.pending ? 'Uploading' : 'Ready'}
                </span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 8, paddingTop: 10, borderTop: `1px solid ${c.line}` }}>
                <span style={{ fontFamily: MONO, fontSize: 12 }}>sha256 {f.sha_short || '…'}</span>
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
          value={caption} onChange={(e) => setCaption(e.target.value)}
          placeholder="Paste the caption, post text or claim that came with the media, with its date if known."
          style={{ ...field, minHeight: 84, padding: '12px 14px', lineHeight: 1.5, resize: 'vertical', background: c.surface }}
        />
        <span style={{ fontFamily: MONO, fontSize: 11.5, color: c.ink2 }}>{caption.length} characters{captionSent && captionSent === caption.trim() ? ' · saved and sealed' : ''}</span>
      </section>

      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: 14, paddingTop: 4 }}>
        <span style={{ fontSize: 13, color: c.ink2 }}>{hosted ? 'Runs on the TruthLens server.' : 'Runs on this device.'} Estimated time 40–60 s.</span>
        <div style={{ display: 'flex', gap: 10 }}>
          <SecondaryButton onClick={saveDraft} disabled={busy} style={{ height: 42, padding: '0 18px' }}>Save draft</SecondaryButton>
          <PrimaryButton onClick={start} disabled={busy || (!evidence.length && !caption.trim())} style={{ opacity: busy || (!evidence.length && !caption.trim()) ? 0.55 : 1 }}>Start analysis<Icon name="arrow_forward" size={19} /></PrimaryButton>
        </div>
      </div>
    </div>
  );
}
