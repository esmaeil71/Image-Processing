import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { uploadStudy } from "../api";

export default function UploadPage() {
  const { t } = useTranslation();
  const nav = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setMsg(null);
    try {
      const st = await uploadStudy(file, title || undefined);
      nav(`/study/${st.id}`);
    } catch (ex: any) {
      setMsg(ex?.response?.data?.detail || "Upload failed");
    }
  }

  return (
    <div>
      <h1>{t("upload")}</h1>
      <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 480 }}>
        <label>
          Title (optional)
          <input value={title} onChange={(e) => setTitle(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
        </label>
        <label>
          File (.dcm / .zip / .nii / .nii.gz)
          <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} style={{ marginTop: 8 }} />
        </label>
        {msg && <div style={{ color: "#f87171" }}>{String(msg)}</div>}
        <button type="submit" disabled={!file} style={{ padding: 10 }}>
          {t("upload")}
        </button>
      </form>
    </div>
  );
}
