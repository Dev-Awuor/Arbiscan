import { useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";

const KES = (n) =>
  "KES " + Number(n).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

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

  const setLeg = (i, key, val) =>
    setLegs((ls) => ls.map((l, k) => (k === i ? { ...l, [key]: val } : l)));
  const addLeg = () =>
    setLegs((ls) => (ls.length < 8 ? [...ls, { label: `Outcome ${String.fromCharCode(65 + ls.length)}`, odds: "" }] : ls));
  const removeLeg = (i) =>
    setLegs((ls) => (ls.length > 2 ? ls.filter((_, k) => k !== i) : ls));

  async function calculate(e) {
    e.preventDefault();
    setError(""); setResult(null); setBusy(true);
    try {
      const odds = legs.map((l) => parseFloat(l.odds));
      const payload = { odds };
      if (mode === "stake") payload.total_stake = parseFloat(amount);
      else payload.target_profit = parseFloat(amount);
      const { data } = await api.post("/calc/", payload);
      setResult({ ...data, labels: legs.map((l) => l.label) });
    } catch (err) {
      const d = err.response?.data;
      setError(d?.odds?.[0] || d?.non_field_errors?.[0] || d?.error || "Could not calculate. Check your odds.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <h1>Arbitrage Calculator</h1>
        <span className="tag tag-free">FREE · no account</span>
      </div>
      <p className="lead">
        Enter the decimal odds you can get for each outcome from different bookmakers.
        We compute the exact stake on each side and tell you whether it locks in a
        <strong> guaranteed profit</strong> — a <em>sure bet</em> — no matter who wins.
      </p>

      <div className="grid">
        <section className="card">
          <h2>Your odds</h2>
          <form onSubmit={calculate}>
            {legs.map((leg, i) => (
              <div className="leg-row" key={i}>
                <input className="leg-label" value={leg.label}
                  onChange={(e) => setLeg(i, "label", e.target.value)} placeholder={`Outcome ${i + 1}`} />
                <input className="leg-odds" type="number" step="0.001" min="1.001"
                  value={leg.odds} onChange={(e) => setLeg(i, "odds", e.target.value)} placeholder="odds" required />
                <button type="button" className="x-btn" onClick={() => removeLeg(i)}
                  disabled={legs.length <= 2} title="Remove">×</button>
              </div>
            ))}
            <button type="button" className="link-btn" onClick={addLeg} disabled={legs.length >= 8}>
              + add outcome
            </button>

            <div className="mode-row">
              <label><input type="radio" checked={mode === "stake"} onChange={() => setMode("stake")} /> Total stake</label>
              <label><input type="radio" checked={mode === "profit"} onChange={() => setMode("profit")} /> Target profit</label>
              <input className="amount" type="number" min="1" value={amount} onChange={(e) => setAmount(e.target.value)} />
            </div>

            <button className="btn" disabled={busy}>{busy ? "Calculating…" : "Calculate stakes"}</button>
          </form>
          {error && <p className="error">{error}</p>}
        </section>

        <section className="card">
          <h2>Result</h2>
          {!result && <p className="muted">Enter odds and press calculate — your stake plan appears here.</p>}
          {result && (
            <>
              <div className={`verdict ${result.is_arb ? "arb" : "noarb"}`}>
                {result.is_arb
                  ? `✅ SURE BET · +${result.margin_pct}% margin · ${result.roi_pct}% ROI`
                  : `⚠️ NOT AN ARB · ${result.overround_pct}% bookmaker overround`}
              </div>
              <table className="result-table">
                <thead><tr><th>Stake</th><th>On</th><th>Odds</th><th>Returns</th></tr></thead>
                <tbody>
                  {result.per_leg.map((leg, i) => (
                    <tr key={i}>
                      <td><strong>{KES(leg.stake)}</strong></td>
                      <td>{result.labels[i]}</td><td>{leg.odds}</td><td>{KES(leg.payout)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="totals">
                <div><span>Total outlay</span><strong>{KES(result.total_stake)}</strong></div>
                <div><span>Guaranteed return</span><strong>{KES(result.guaranteed_payout)}</strong></div>
                <div className={result.profit >= 0 ? "pos" : "neg"}>
                  <span>Profit</span><strong>{KES(result.profit)} ({result.roi_pct}% ROI)</strong>
                </div>
              </div>
              {!result.is_arb && (
                <p className="muted small">
                  These odds don't guarantee profit — implied probabilities sum above 100%.
                  Our <Link to="/live">live sure-bets</Link> find real arbs for you automatically.
                </p>
              )}
            </>
          )}
        </section>
      </div>

      {/* Educational explainer (inspired by best-in-class tools) */}
      <section className="card explainer">
        <h2>How the arbitrage calculator works</h2>
        <p>
          An <strong>arbitrage bet</strong> (or “arb”/“sure bet”) happens when different
          bookmakers price the same event so generously that you can back <em>every</em>
          outcome and still come out ahead. The calculator works out how much to put on each
          side so your return is identical regardless of the result.
        </p>
        <ol className="steps">
          <li><strong>Enter the odds</strong> in decimal format (e.g. 2.10) for each outcome — ideally the best price from a different book per side.</li>
          <li><strong>Pick a mode:</strong> a fixed <em>total stake</em> (how much you’ll wager in total) or a <em>target profit</em> (how much you want to win).</li>
          <li><strong>Read the plan:</strong> we split your stake by each outcome’s implied probability so every result pays the same.</li>
          <li><strong>Check the verdict:</strong> if the implied probabilities sum below 100%, it’s a guaranteed profit. Above 100% means the book’s margin (“overround”) eats the edge — not an arb.</li>
        </ol>
        <div className="example">
          <h3>Worked example</h3>
          <p>
            Two books price a tennis match at <strong>2.10</strong> for Player A and
            <strong> 2.10</strong> for Player B. Implied probability is 1/2.10 + 1/2.10 = 95.2%
            — below 100%, so it’s an arb. Staking KES 10,000 → KES 5,000 on each side. Whoever
            wins, you collect KES 10,500: a <strong>guaranteed KES 500 (5% ROI)</strong>.
          </p>
        </div>
        <p className="muted small">
          Tip: place the <strong>longer-odds leg first</strong> — it’s the one most likely to
          move or be limited. Want the arbs found for you across live markets?
          See <Link to="/pricing">Premium</Link>.
        </p>
      </section>
    </>
  );
}
