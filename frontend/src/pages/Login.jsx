import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useAuth } from "../auth";
import AuthLayout from "./AuthLayout";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [username, setU] = useState("");
  const [password, setP] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      await login(username, password);
      nav("/app");
    } catch {
      setError("That username and password don't match.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Welcome back" subtitle="Log in to see today's arbs."
      footer={<>New here? <Link to="/register">Create an account</Link></>}>
      <form onSubmit={submit}>
        <label>Username<input autoComplete="username" value={username} onChange={(e) => setU(e.target.value)} required /></label>
        <label>Password<input type="password" autoComplete="current-password" value={password} onChange={(e) => setP(e.target.value)} required /></label>
        <button className="pill pill-accent pill-lg" disabled={busy}>{busy ? "Logging in…" : <>Log in <ArrowRight size={18} /></>}</button>
      </form>
      {error && <p className="auth-error" role="alert">{error}</p>}
    </AuthLayout>
  );
}
