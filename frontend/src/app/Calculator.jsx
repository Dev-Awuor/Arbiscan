import { useState } from "react";
import { Plus, X, AlertCircle } from "lucide-react";
import api from "../api";
import { KES } from "../format";

export default function Calculator() {
  const [legs, setLegs] = useState([
    { label: "Outcome A", odds: "2.10" },
    { label: "Outcome B", odds: "2.10" },
  ]);
  const [mode, setMode] = useState("stake");
  const [amount, setAmount] = useState("10000");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const setLeg = (i, key, val) => setLegs((ls) => ls.map((l, k) => (k === i ? { ...l, [key]: val } : l)));
  const addLeg = () => setLegs((ls) => (ls.length < 8 ? [...ls, { label: `Outcome ${String.fromCharCode(65 + ls.length)}`, odds: "" }] : ls));
  const removeLeg = (i) => setLegs((ls) => (ls.length > 2 ? ls.filter((_, k) => k !== i) : ls));

  async function calculate(e) {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      const payload = { odds: legs.map((l) => parseFloat(l.odds)) };
      if (mode === "stake") payload.total_stake = parseFloat(amount);
      else payload.target_profit = parseFloat(amount);
      const { data } = await api.post("/calc/", payload);
      setResult({ ...data, labels: legs.map((l) => l.label) });
    } catch (err) {
      const d = err.response?.data;
      setError(d?.odds?.[0] || d?.non_field_errors?.[0] || d?.error || "Could not calculate. Check the odds and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-title">
        <div>
          <h1>Calculator</h1>
          <p>Split a stake across 2 to 8 outcomes so every result returns the same amount.</p>
        </div>
      </div>

      <div className="calc">
        <form className="card" onSubmit={calculate}>
          <div className="card-header"><div><h2 className="card-title">Odds</h2><p className="card-desc">Decimal odds, ideally the best price for each outcome.</p></div></div>
          <div className="card-content">
            <div className="legs">
              {legs.map((leg, i) => (
                <div className="leg" key={i}>
                  <input className="input" value={leg.label} aria-label={`Outcome ${i + 1} name`} onChange={(e) => setLeg(i, "label", e.target.value)} />
                  <input className="input" type="number" step="0.001" min="1.001" inputMode="decimal" required
                    aria-label={`Outcome ${i + 1} odds`} value={leg.odds} onChange={(e) => setLeg(i, "odds", e.target.value)} />
                  <button type="button" className="btn btn-ghost btn-icon" onClick={() => removeLeg(i)}
                    disabled={legs.length <= 2} aria-label={`Remove outcome ${i + 1}`}><X /></button>
                </div>
              ))}
            </div>
            <button type="button" className="btn btn-outline btn-sm" style={{ marginTop: 12 }} onClick={addLeg} disabled={legs.length >= 8}>
              <Plus />Add outcome
            </button>
          </div>
          <div className="card-footer">
            <div className="tabs" role="group" aria-label="Size by">
              <button type="button" aria-pressed={mode === "stake"} onClick={() => setMode("stake")}>Total stake</button>
              <button type="button" aria-pressed={mode === "profit"} onClick={() => setMode("profit")}>Target profit</button>
            </div>
            <span className="addon" style={{ flex: 1, minWidth: 140 }}><span>KES</span>
              <input className="input" type="number" min="1" inputMode="decimal" required value={amount}
                aria-label={mode === "stake" ? "Total stake" : "Target profit"} onChange={(e) => setAmount(e.target.value)} />
            </span>
            <button className="btn" disabled={busy}>{busy ? "Calculating…" : "Calculate"}</button>
          </div>
          {error && <div className="alert alert-error" style={{ margin: "0 20px 20px" }}><AlertCircle />{error}</div>}
        </form>

        <div className="card" aria-live="polite">
          <div className="card-header"><div><h2 className="card-title">Stake split</h2><p className="card-desc">What to place at each bookmaker.</p></div></div>
          {!result ? (
            <div className="card-content"><p className="muted">Enter odds and press Calculate.</p></div>
          ) : (
            <div className="card-content" style={{ padding: "16px 0 20px" }}>
              <div style={{ padding: "0 20px" }}>
                <div className={`calc-status${result.is_arb ? " ok" : ""}`}>
                  <strong>{result.is_arb ? "Guaranteed profit" : "No arbitrage"}</strong>
                  <span className="muted num">
                    {result.is_arb ? `${result.margin_pct}% margin · ${result.roi_pct}% return` : `Bookmaker margin ${result.overround_pct}%`}
                  </span>
                </div>
              </div>
              <div className="table-wrap">
                <table className="table">
                  <thead><tr><th>Outcome</th><th className="r">Odds</th><th className="r">Stake</th><th className="r">Return</th></tr></thead>
                  <tbody>
                    {result.per_leg.map((leg, i) => (
                      <tr key={i}>
                        <td>{result.labels[i]}</td>
                        <td className="r">{leg.odds.toFixed(2)}</td>
                        <td className="r cell-main">{KES(leg.stake)}</td>
                        <td className="r">{KES(leg.payout)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <dl className="totals">
                <div><dt>Total stake</dt><dd>{KES(result.total_stake)}</dd></div>
                <div><dt>Minimum return</dt><dd>{KES(result.guaranteed_payout)}</dd></div>
                <div><dt>Profit</dt><dd className={result.profit >= 0 ? "pos" : ""} style={result.profit < 0 ? { color: "#dc2626" } : undefined}>{KES(result.profit)}</dd></div>
              </dl>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
