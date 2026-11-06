import axios from "axios";

/**
 * If VITE_API_URL is empty, use same-origin + Vite dev proxy (/api → backend).
 * Set VITE_API_URL explicitly when serving a production build or a custom deployment.
 */
function apiBaseUrl(): string {
  const raw = import.meta.env.VITE_API_URL;
  if (raw != null && String(raw).trim() !== "") {
    return String(raw).replace(/\/$/, "");
  }
  return "";
}

const base = apiBaseUrl();
export const api = axios.create({ baseURL: base ? `${base}/api/v1` : "/api/v1" });

export function setAuth(token: string | null) {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
    localStorage.setItem("token", token);
  } else {
    delete api.defaults.headers.common.Authorization;
    localStorage.removeItem("token");
  }
}

const t = localStorage.getItem("token");
if (t) setAuth(t);

export async function login(email: string, password: string) {
  const body = new URLSearchParams();
  body.set("username", email);
  body.set("password", password);
  const r = await api.post("/auth/login", body, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return r.data as { access_token: string };
}

export async function fetchStudies() {
  const r = await api.get("/studies/");
  return r.data;
}

export async function uploadStudy(file: File, title?: string) {
  const fd = new FormData();
  fd.append("file", file);
  if (title) fd.append("title", title);
  // Large medical files — long timeout (ms); 0 = no limit where supported
  const r = await api.post("/studies/upload", fd, { timeout: 0 });
  return r.data;
}

export async function getStudy(id: string) {
  const r = await api.get(`/studies/${id}`);
  return r.data;
}

export async function viewerInfo(id: string) {
  const r = await api.get(`/studies/${id}/viewer`);
  return r.data;
}

export async function volumeUrl(studyId: string, seriesId: string) {
  const r = await api.get(`/studies/${studyId}/series/${seriesId}/volume-url`);
  return r.data as { url: string };
}

export async function listModels() {
  const r = await api.get("/models/");
  return r.data;
}

export async function createJob(seriesId: string, modelId?: string) {
  const r = await api.post("/jobs/", { series_id: seriesId, model_id: modelId ?? null });
  return r.data;
}

export async function pollJob(jobId: string) {
  const r = await api.get(`/jobs/${jobId}`);
  return r.data;
}

export async function jobResult(jobId: string) {
  const r = await api.get(`/jobs/${jobId}/result`);
  return r.data;
}

export async function uploadUserMask(jobId: string, file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const r = await api.post(`/jobs/${jobId}/user-mask`, fd, { timeout: 0 });
  return r.data;
}
