import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
// The Leaflet adapter's published compatibility build imports the renderer with
// require(); resolve that bare import to MapLibre 6's ESM entry for bundling.
export default defineConfig({ plugins: [vue()], resolve: { alias: [{ find: /^maplibre-gl$/, replacement: 'maplibre-gl/dist/maplibre-gl.mjs' }] }, server: { proxy: { '/api': 'http://127.0.0.1:8787' } }, test: { environment: 'jsdom', include: ['tests/**/*.test.ts'] } })
