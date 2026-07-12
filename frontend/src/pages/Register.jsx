import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../auth";

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
      nav("/live");
    } catch (err) {
      const d = err.response?.data;
      setError(d?.username?.[0] || d?.password?.[0] || "Could not register.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card narrow">
      <h1>Create a free account</h1>
      <p className="muted">The calculator is free without an account. Sign up to unlock the live sure-bets feed (premium).</p>
      <form onSubmit={submit}>
        <label>Username<input value={username} onChange={(e) => setU(e.target.value)} required /></label>
        <label>Email (optional)<input type="email" value={email} onChange={(e) => setE(e.target.value)} /></label>
        <label>Password<input type="password" value={password} onChange={(e) => setP(e.target.value)} minLength={8} required /></label>
        <button className="btn" disabled={busy}>{busy ? "…" : "Sign up"}</button>
      </form>
      {error && <p className="error">{error}</p>}
      <p className="muted">Already have an account? <Link to="/login">Log in</Link></p>
    </div>
  );
}
