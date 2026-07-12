import { useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import { useAuth } from "../auth";

export default function Pricing() {
  const { user, isPremium } = useAuth();
  const [msg, setMsg] = useState("");

  async function upgrade() {
    setMsg("");
    try {
      const { data } = await api.post("/auth/checkout/", { plan: "premium" });
      setMsg(data.message || "Checkout started.");
    } catch {
      setMsg("Please log in first.");
    }
  }

  return (
    <>
      <div className="page-head"><h1>Plans &amp; Pricing</h1></div>
      <p className="lead">
        The calculator is free forever. Upgrade to have profitable sure-bets found for you across live markets.
      </p>

      <div className="trust trust-top">
        <span>📚 Multi-book coverage</span><span>🏆 40+ leagues (roadmap)</span>
        <span>🛡️ Guaranteed-profit math</span><span>🧮 Auto stake sizing</span>
      </div>

      <div className="pricing">
        <div className="card plan">
          <h2>Free</h2>
          <p className="price">KES 0</p>
          <ul>
            <li>✓ Arbitrage calculator (any odds)</li>
            <li>✓ Stake split &amp; guaranteed-profit math</li>
            <li>✓ Live sure-bets preview (up to 1% ROI)</li>
            <li className="off">— Higher-profit arbs (above 1% ROI)</li>
            <li className="off">— Signed PDF reports</li>
          </ul>
          <Link to="/" className="btn btn-ghost">Use the calculator</Link>
        </div>

        <div className="card plan">
          <h2>Core</h2>
          <p className="price">KES 1,000<span>/mo</span></p>
          <ul>
            <li>✓ Everything in Free</li>
            <li>✓ <strong>Every pre-game arb</strong>, all ROI levels</li>
            <li>✓ Ready-to-place stakes sized to your target</li>
            <li>✓ Signed, QR-traceable PDF reports</li>
            <li className="off">— Live in-game arbs</li>
          </ul>
          {isPremium
            ? <div className="badge badge-prem big">Active ✓</div>
            : <button className="btn btn-ghost" onClick={upgrade} disabled={!user}>{user ? "Choose Core" : "Log in to upgrade"}</button>}
        </div>

        <div className="card plan featured">
          <span className="ribbon">Recommended</span>
          <h2>Pro</h2>
          <p className="price">KES 1,500<span>/mo</span></p>
          <ul>
            <li>✓ Everything in Core</li>
            <li>✓ <strong>Live, in-game arbs</strong> as odds move</li>
            <li>✓ Auto-refresh feed &amp; priority scans</li>
            <li>✓ Tennis · Basketball · MMA · World Cup</li>
          </ul>
          {isPremium
            ? <div className="badge badge-prem big">You're Premium ✓</div>
            : <button className="btn" onClick={upgrade} disabled={!user}>{user ? "Start 7-Day Free Trial" : "Log in to upgrade"}</button>}
        </div>
      </div>

      {msg && <p className="muted small center">{msg}</p>}
      <p className="muted small center">
        Payments are not wired yet — premium is granted manually during this phase. Bet responsibly (18+).
      </p>
    </>
  );
}
