import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { jobResult, pollJob, uploadUserMask } from "../api";

export default function ResultPage() {
  const { jobId } = useParams();
  const [job, setJob] = useState<any>(null);
  const [res, setRes] = useState<any>(null);
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    if (!jobId) return;
    let timer: number | undefined;
    const tick = async () => {
      const j = await pollJob(jobId);
      setJob(j);
      if (j.status === "completed" || j.status === "failed") {
        const r = await jobResult(jobId);
        setRes(r);
        if (timer) window.clearInterval(timer);
      }
    };
    void tick();
    timer = window.setInterval(() => void tick(), 2000);
    return () => {
      if (timer) window.clearInterval(timer);
    };
  }, [jobId]);

  async function onSave(e: FormEvent) {
    e.preventDefault();
    if (!jobId || !file) return;
    await uploadUserMask(jobId, file);
    const r = await jobResult(jobId);
    setRes(r);
  }

  return (
    <div>
      <Link to="/">← Studies</Link>
      <h1>Job result</h1>
      {!job && <p>Loading…</p>}
      {job && (
        <div>
          <div>Status: {job.status}</div>
          {job.error_message && <div style={{ color: "#f87171" }}>{job.error_message}</div>}
          <div>Runtime: {job.runtime_seconds ?? "—"} s</div>
        </div>
      )}
      {res && (
        <div style={{ marginTop: 16 }}>
          {res.overlay_url && (
            <div>
              <h3>Overlay (preview)</h3>
              <img src={res.overlay_url} alt="overlay" style={{ maxWidth: "100%", border: "1px solid #334155" }} />
            </div>
          )}
          {res.mask_url && (
            <p>
              <a href={res.mask_url} download style={{ color: "#38bdf8" }}>
                Download mask NIfTI
              </a>
            </p>
          )}
        </div>
      )}
      <form onSubmit={onSave} style={{ marginTop: 24 }}>
        <h3>Upload edited mask (NIfTI)</h3>
        <input type="file" accept=".nii,.gz" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        <button type="submit" disabled={!file} style={{ marginLeft: 8 }}>
          Save user mask
        </button>
      </form>
    </div>
  );
}
