// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path';
//import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000,
        open: true
    },
    preview: {
        port: 8080
    },
    build: {
        outDir: 'dist',
        assetsDir: 'assets',
        sourcemap: false,
        minify: 'terser',
    },
    resolve: {
        alias: {
            '@': path.resolve(__dirname, 'src'),
        },
    },

})