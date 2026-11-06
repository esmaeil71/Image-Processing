import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { login, setAuth } from "../api";

export default function Login() {
  const { t } = useTranslation();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      const r = await login(email, password);
      setAuth(r.access_token);
      nav("/", { replace: true });
    } catch (e: unknown) {
      const ax = e as { response?: { data?: { detail?: string } }; message?: string };
      const detail = ax.response?.data?.detail;
      const net = ax.message;
      setErr(
        typeof detail === "string"
          ? detail
          : net && (net.includes("Network") || net.includes("ERR_"))
            ? "Cannot reach API — check VITE_API_URL matches backend URL/port."
            : "Invalid credentials"
      );
    }
  }

  return (
    <div style={{ maxWidth: 400 }}>
      <h1>{t("login")}</h1>
      <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <label>
          {t("email")}
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ width: "100%", padding: 8, marginTop: 4 }}
          />
        </label>
        <label>
          {t("password")}
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ width: "100%", padding: 8, marginTop: 4 }}
          />
        </label>
        {err && <div style={{ color: "#f87171" }}>{err}</div>}
        <button type="submit" style={{ padding: 10, cursor: "pointer" }}>
          {t("login")}
        </button>
      </form>
    </div>
  );
}
