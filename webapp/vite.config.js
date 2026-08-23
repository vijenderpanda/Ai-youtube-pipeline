import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

// S4 · deliverable #2 — client-side live preview via @remotion/player.
// The webapp renders the EXACT production composition (remotion-studio/src/Short.tsx)
// unchanged, so preview === render (no fork of the composition). Two things make
// that safe:
//   • alias '@remotion-src' → ../remotion-studio/src so the app imports the real
//     Short + cookbook components, and server.fs.allow lets Vite dev read them
//     from outside the webapp root (prod build bundles them, so fs.allow is
//     dev-only);
//   • dedupe react/react-dom/remotion/@remotion/player — WITHOUT this, Node
//     resolution would pull remotion-studio/node_modules/react@19 for Short.tsx
//     ALONGSIDE the webapp's react@18, giving two React copies and an invalid-hook
//     crash. Dedupe forces one copy (the webapp's) for both.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@remotion-src': fileURLToPath(new URL('../remotion-studio/src', import.meta.url)),
    },
    dedupe: ['react', 'react-dom', 'remotion', '@remotion/player'],
  },
  server: { fs: { allow: ['..'] } },
})
