import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';

export default defineConfig({
    base: './',
    plugins: [react()],
    server: {
        proxy: {
            '/player/jobs': 'http://localhost:5000',
            '/player_v2': 'http://localhost:5000',
            '/job': 'http://localhost:5000',
        },
    },
    build: {
        outDir: 'dist',
    },
});
