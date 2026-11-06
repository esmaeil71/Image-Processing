import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import UploadPage from "./pages/UploadPage";
import StudyPage from "./pages/StudyPage";
import ResultPage from "./pages/ResultPage";

function Shell({ children }: { children: React.ReactNode }) {
  const { t, i18n } = useTranslation();
  const isRtl = i18n.language === "fa";
  useEffect(() => {
    document.documentElement.lang = i18n.language;
    document.documentElement.dir = isRtl ? "rtl" : "ltr";
  }, [i18n.language, isRtl]);

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", minHeight: "100vh", background: "#0f172a", color: "#e2e8f0" }}>
      <header
        style={{
          padding: "12px 24px",
          borderBottom: "1px solid #334155",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 16,
        }}
      >
        <strong>{t("app_title")}</strong>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <label style={{ fontSize: 13 }}>
            {t("language")}:{" "}
            <select
              value={i18n.language}
              onChange={(e) => {
                const lng = e.target.value;
                void i18n.changeLanguage(lng);
                localStorage.setItem("lng", lng);
              }}
            >
              <option value="en">English</option>
              <option value="fa">فارسی</option>
            </select>
          </label>
        </div>
      </header>
      <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>{children}</div>
      <footer style={{ padding: 16, fontSize: 12, color: "#94a3b8", textAlign: "center" }}>{t("disclaimer")}</footer>
    </div>
  );
}

function RequireAuth({ children }: { children: JSX.Element }) {
  const token = localStorage.getItem("token");
  const nav = useNavigate();
  useEffect(() => {
    if (!token) nav("/login", { replace: true });
  }, [token, nav]);
  if (!token) return null;
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <Dashboard />
              </RequireAuth>
            }
          />
          <Route
            path="/upload"
            element={
              <RequireAuth>
                <UploadPage />
              </RequireAuth>
            }
          />
          <Route
            path="/study/:id"
            element={
              <RequireAuth>
                <StudyPage />
              </RequireAuth>
            }
          />
          <Route
            path="/result/:jobId"
            element={
              <RequireAuth>
                <ResultPage />
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Shell>
    </BrowserRouter>
  );
}
