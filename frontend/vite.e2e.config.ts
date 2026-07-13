// TEMPORARY e2e config — proxies to the backend on :8100. Safe to delete.
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  server: {
    port: 3100,
    proxy: {
      '/api': { target: 'http://localhost:8100', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8100', ws: true },
    },
  },
});
