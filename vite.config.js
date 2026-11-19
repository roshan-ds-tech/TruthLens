import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => ({
  plugins: [react(), {
    name: 'public-api-address',
    generateBundle() {
      const env = loadEnv(mode, process.cwd(), 'VITE_');
      this.emitFile({ type: 'asset', fileName: 'api-config.json',
        source: JSON.stringify({ apiBase: env.VITE_API_BASE || '' }) });
    },
  }],
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
}));
