import { Link } from "react-router-dom";
import Waves from "../Waves";
import "./landing.css";
import "./auth.css";

export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="lp auth-page">
      <aside className="auth-brand">
        <Waves className="hero-waves" />
        <Link to="/" className="lp-logo"><span className="lp-mark" />arbiscan</Link>
        <div className="auth-quote">
          <p>Two books, one match, opposite prices.</p>
          <p className="hl">That's the whole trick.</p>
        </div>
        <span className="auth-foot">18+. Bet responsibly.</span>
      </aside>
      <main className="auth-main">
        <Link to="/" className="lp-logo dark auth-mobile-logo"><span className="lp-mark" />arbiscan</Link>
        <div className="auth-card">
          <h1>{title}</h1>
          <p className="auth-sub">{subtitle}</p>
          {children}
          <p className="auth-switch">{footer}</p>
        </div>
      </main>
    </div>
  );
}
