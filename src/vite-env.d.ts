// src/vite-env.d.ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_API_URL: string;
    readonly VITE_ENABLE_MOCK: boolean;
    readonly VITE_TOAST_DURATION: number;
    readonly VITE_MAX_UPLOAD_SIZE: number;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}