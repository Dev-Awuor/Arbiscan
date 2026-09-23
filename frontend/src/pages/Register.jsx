import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useAuth } from "../auth";
import AuthLayout from "./AuthLayout";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [username, setU] = useState("");
  const [email, setE] = useState("");
  const [password, setP] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      await register(username, email, password);
      nav("/app");
    } catch (err) {
      const d = err.response?.data;
      setError(d?.username?.[0] || d?.email?.[0] || d?.password?.[0] || "Could not create the account. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Create your account" subtitle="Free. Takes about ten seconds."
      footer={<>Already have one? <Link to="/login">Log in</Link></>}>
      <form onSubmit={submit}>
        <label>Username<input autoComplete="username" value={username} onChange={(e) => setU(e.target.value)} required /></label>
        <label>Email (optional)<input type="email" autoComplete="email" value={email} onChange={(e) => setE(e.target.value)} /></label>
        <label>Password, at least 8 characters<input type="password" autoComplete="new-password" value={password} onChange={(e) => setP(e.target.value)} minLength={8} required /></label>
        <button className="pill pill-accent pill-lg" disabled={busy}>{busy ? "Creating account…" : <>Create account <ArrowRight size={18} /></>}</button>
      </form>
      {error && <p className="auth-error" role="alert">{error}</p>}
    </AuthLayout>
  );
}
