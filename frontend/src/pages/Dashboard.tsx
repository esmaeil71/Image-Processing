import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { fetchStudies } from "../api";

export default function Dashboard() {
  const { t } = useTranslation();
  const [studies, setStudies] = useState<any[]>([]);
  const [q, setQ] = useState("");

  useEffect(() => {
    void (async () => {
      const s = await fetchStudies();
      setStudies(s);
    })();
  }, []);

  const filtered = studies.filter((s) => (q ? String(s.title || "").toLowerCase().includes(q.toLowerCase()) : true));

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>{t("studies")}</h1>
        <Link to="/upload" style={{ color: "#38bdf8" }}>
          + {t("upload")}
        </Link>
      </div>
      <input
        placeholder="Search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        style={{ width: "100%", maxWidth: 320, padding: 8, marginBottom: 16 }}
      />
      <ul style={{ listStyle: "none", padding: 0 }}>
        {filtered.map((s) => (
          <li
            key={s.id}
            style={{
              marginBottom: 8,
              padding: 12,
              border: "1px solid #334155",
              borderRadius: 8,
              display: "flex",
              justifyContent: "space-between",
            }}
          >
            <div>
              <div style={{ fontWeight: 600 }}>{s.title || s.id}</div>
              <div style={{ fontSize: 12, color: "#94a3b8" }}>{s.status}</div>
            </div>
            <Link to={`/study/${s.id}`} style={{ color: "#38bdf8" }}>
              Open
            </Link>
          </li>
        ))}
      </ul>
      <p style={{ fontSize: 12, color: "#94a3b8" }}>Sample data label: demo_synthetic (if used)</p>
    </div>
  );
}
