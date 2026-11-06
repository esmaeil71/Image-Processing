/** Normalize FastAPI / axios error payloads for display */

export function formatApiError(err: unknown): string {
  const e = err as {
    code?: string;
    message?: string;
    response?: { data?: { detail?: unknown } };
  };
  if (e.code === "ECONNABORTED") {
    return "زمان درخواست تمام شد — فایل خیلی بزرگ است یا سرور کند است. / Request timed out.";
  }
  const msg = e.message;
  if (msg && (msg.includes("Network Error") || msg.includes("ERR_") || msg.includes("Failed to fetch"))) {
    return "ارتباط با API برقرار نشد — مطمئن شوید docker compose بالا است. / Cannot reach API.";
  }
  const d = e.response?.data?.detail;
  if (d === undefined || d === null) {
    return msg || "Upload failed";
  }
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d
      .map((x: unknown) => {
        if (x && typeof x === "object" && "msg" in (x as object)) {
          return String((x as { msg: string }).msg);
        }
        return String(x);
      })
      .join("; ");
  }
  if (typeof d === "object" && d !== null && "msg" in d) {
    return String((d as { msg: string }).msg);
  }
  try {
    return JSON.stringify(d);
  } catch {
    return String(d);
  }
}
