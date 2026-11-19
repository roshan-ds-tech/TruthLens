// <img> for protected files: fetched with the session token, shown from an object URL.
import { useEffect } from 'react';
import { useApi, useMediaUrl } from './client.js';

export function AuthImg({ path, onError, ...rest }) {
  const { url, error } = useMediaUrl(path);
  useEffect(() => { if (error) onError?.(error); }, [error]); // eslint-disable-line react-hooks/exhaustive-deps
  return url ? <img src={url} {...rest} /> : null;
}

/** Preview drawn from the evidence itself: waveform bars for audio, the opening lines for text. */
export function EvidencePreview({ ev, dark = false, lines = 4 }) {
  const isAudio = ev?.kind === 'audio', isText = ev?.kind === 'text';
  const wf = useApi(isAudio ? `/evidence/${ev.id}/waveform` : null);
  const detail = useApi(isText ? `/evidence/${ev.id}` : null);
  const ink = dark ? '#E8E8E4' : 'var(--tl-ink,#111)';
  if (isAudio && wf.data?.peaks?.length) {
    const peaks = wf.data.peaks.filter((_, i) => i % 2 === 0);
    return (
      <div style={{ position: 'absolute', inset: '18% 8%', display: 'flex', alignItems: 'center', gap: 1 }}>
        {peaks.map((p, i) => <span key={i} style={{ flex: 1, height: `${Math.max(p, 0.03) * 100}%`, background: ink, opacity: 0.8, borderRadius: 1 }} />)}
      </div>
    );
  }
  if (isText && detail.data?.text) {
    return (
      <div style={{ position: 'absolute', inset: 0, padding: '14% 10%', display: 'flex', alignItems: 'center' }}>
        <span style={{ fontSize: 12.5, lineHeight: 1.45, color: ink, display: '-webkit-box', WebkitLineClamp: lines, WebkitBoxOrient: 'vertical', overflow: 'hidden', fontStyle: 'italic' }}>
          “{detail.data.text}”
        </span>
      </div>
    );
  }
  return null;
}
