import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../auth";

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
      nav("/live");
    } catch {
      setError("Invalid username or password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card narrow">
      <h1>Log in</h1>
      <form onSubmit={submit}>
        <label>Username<input value={username} onChange={(e) => setU(e.target.value)} required /></label>
        <label>Password<input type="password" value={password} onChange={(e) => setP(e.target.value)} required /></label>
        <button className="btn" disabled={busy}>{busy ? "…" : "Log in"}</button>
      </form>
      {error && <p className="error">{error}</p>}
      <p className="muted">No account? <Link to="/register">Sign up free</Link></p>
    </div>
  );
}
