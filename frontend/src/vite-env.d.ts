/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Empty string = use Vite proxy in dev (recommended in Docker). */
  readonly VITE_API_URL?: string;
  readonly VITE_ORTHANC_DICOMWEB: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
