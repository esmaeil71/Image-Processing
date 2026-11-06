import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Niivue } from "@niivue/niivue";
import { createJob, getStudy, listModels, viewerInfo, volumeUrl } from "../api";

export default function StudyPage() {
  const { id } = useParams();
  const { t } = useTranslation();
  const [study, setStudy] = useState<any>(null);
  const [vinfo, setVinfo] = useState<any>(null);
  const [models, setModels] = useState<any[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!id) return;
    void (async () => {
      const s = await getStudy(id);
      setStudy(s);
      const vi = await viewerInfo(id);
      setVinfo(vi);
      const m = await listModels();
      setModels(m);
    })();
  }, [id]);

  useEffect(() => {
    if (!study || !id || !canvasRef.current) return;
    const niftiSeries = study.series?.find((x: any) => x.storage_type === "nifti_s3");
    if (!niftiSeries) return;
    let cancelled = false;
    void (async () => {
      try {
        const { url } = await volumeUrl(id, niftiSeries.id);
        if (cancelled) return;
        const nv = new Niivue({ isResizeCanvas: true });
        nv.attachToCanvas(canvasRef.current!);
        await nv.loadVolumes([{ url }]);
      } catch (e) {
        setErr("Could not load NIfTI volume");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [study, id]);

  async function runOnFirstSeries() {
    setErr(null);
    try {
      const niftiSeries = study?.series?.find((x: any) => x.storage_type === "nifti_s3");
      if (!niftiSeries) {
        setErr("No NIfTI series for segmentation in this build.");
        return;
      }
      const model = models.find((m) => m.is_active);
      const j = await createJob(niftiSeries.id, model?.id);
      setJobId(j.id);
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "Job failed");
    }
  }

  if (!study) return <div>Loading…</div>;

  const orthanc = vinfo?.stone_webviewer;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <h1>{study.title}</h1>
        <Link to="/">← {t("studies")}</Link>
      </div>
      <p style={{ fontSize: 12, color: "#94a3b8" }}>
        Output is algorithmic assistance only — not a diagnosis or treatment plan.
      </p>

      {orthanc && (
        <section style={{ marginTop: 16 }}>
          <h2>{t("orthanc_viewer")}</h2>
          <p>
            <a href={orthanc} target="_blank" rel="noreferrer" style={{ color: "#38bdf8" }}>
              Open Orthanc Stone Web viewer (new tab)
            </a>
          </p>
          <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 8 }}>
            DICOMweb root: {vinfo?.dicomweb_root} — StudyInstanceUID: {vinfo?.study_instance_uid}. Authenticate with Orthanc
            credentials if prompted.
          </div>
        </section>
      )}

      {study.series?.some((x: any) => x.storage_type === "nifti_s3") && (
        <section style={{ marginTop: 16 }}>
          <h2>{t("nifti_viewer")}</h2>
          <canvas ref={canvasRef} width={800} height={400} style={{ width: "100%", maxHeight: 400 }} />
        </section>
      )}

      <section style={{ marginTop: 16 }}>
        <button onClick={runOnFirstSeries} style={{ padding: "10px 16px" }}>
          {t("run_model")}
        </button>
        {jobId && (
          <span style={{ marginLeft: 12 }}>
            Job: <Link to={`/result/${jobId}`}>{jobId}</Link>
          </span>
        )}
        {err && <div style={{ color: "#f87171", marginTop: 8 }}>{err}</div>}
      </section>
    </div>
  );
}
