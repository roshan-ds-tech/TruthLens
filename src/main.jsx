import { Component, StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';
import App from './App.jsx';

/** Last line of defence: a rendering error shows a short message instead of a blank page. */
class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('TruthLens UI error', error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div style={{ padding: 40, fontFamily: "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif", color: '#111' }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.12em', textTransform: 'uppercase', color: '#5F5F5A' }}>TruthLens</div>
        <h1 style={{ fontSize: 28, margin: '8px 0' }}>Something went wrong on this screen.</h1>
        <p style={{ color: '#5F5F5A', margin: '0 0 16px' }}>Your cases and evidence are safe on the server. Reload to continue.</p>
        <button onClick={() => window.location.reload()} style={{ height: 40, padding: '0 18px', borderRadius: 999, border: 'none', background: '#FFD23F', fontWeight: 700, cursor: 'pointer' }}>Reload</button>
      </div>
    );
  }
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
);
