// <img> for protected files: fetched with the session token, shown from an object URL.
import { useEffect } from 'react';
import { useMediaUrl } from './client.js';

export function AuthImg({ path, onError, ...rest }) {
  const { url, error } = useMediaUrl(path);
  useEffect(() => { if (error) onError?.(error); }, [error]); // eslint-disable-line react-hooks/exhaustive-deps
  return url ? <img src={url} {...rest} /> : null;
}
