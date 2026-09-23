import { useState } from "react";
import { RefreshCw, AlertCircle, SearchX } from "lucide-react";
import { useApi } from "../api";
import { KES, MARKETS, kickoff } from "../format";

/* One arb with a resizable total stake. Stakes split by implied probability
   so every outcome returns the same amount. */
function Bet({ bet }) {
  const inv = bet.legs.map((l) => 1 / l.odds);
  const sumInv = inv.reduce((a, b) => a + b, 0);
  const [total, setTotal] = useState(String(Math.round(bet.bankroll)));
  const bankroll = parseFloat(total) || 0;
  const stake = (i) => bankroll * (inv[i] / sumInv);
  const profit = bankroll / sumInv - bankroll;
  // Longest odds first: the price most likely to move or be limited.
  const firstIdx = bet.legs.reduce((mi, l, i, a) => (l.odds > a[mi].odds ? i : mi), 0);

  return (
    <div className="card bet">
      <div className="card-header">
        <div>
          <h2 className="card-title">{bet.match}</h2>
          <div className="bet-meta">
            <span className="badge badge-secondary">{MARKETS[bet.market] || bet.market}</span>
            {bet.kickoff && <span className="badge">{kickoff(bet.kickoff)}</span>}
          </div>
        </div>
        <div className="bet-margin"><strong>+{bet.margin_pct.toFixed(2)}%</strong><span>margin</span></div>
      </div>
      <div className="card-content">
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Bookmaker</th><th>Selection</th><th className="r">Odds</th><th className="r">Stake</th><th className="r">Return</th></tr></thead>
            <tbody>
              {bet.legs.map((leg, i) => (
                <tr key={i}>
                  <td className="cell-main">{leg.book} {i === firstIdx && <span className="badge" style={{ marginLeft: 6 }}>place first</span>}</td>
                  <td>{leg.label}</td>
                  <td className="r">{leg.odds.toFixed(2)}</td>
                  <td className="r cell-main">{KES(stake(i))}</td>
                  <td className="r">{KES(stake(i) * leg.odds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="card-footer">
        <label className="stake-inline">Total stake
          <span className="addon"><span>KES</span>
            <input className="input" type="number" min="0" inputMode="decimal" value={total} onChange={(e) => setTotal(e.target.value)} />
          </span>
        </label>
        <span className="muted">Profit <strong className="pos num">{KES(profit)}</strong></span>
      </div>
    </div>
  );
}

export default function SureBets() {
  const [market, setMarket] = useState("");
  const [target, setTarget] = useState("500");
  const [applied, setApplied] = useState({ market: "", target: "500" });
  const q = new URLSearchParams({ target: applied.target, ...(applied.market && { market: applied.market }) });
  const { data, loading, error, reload } = useApi(`/live/sure-bets/?${q}`);

  function apply(e) {
    e.preventDefault();
    if (market === applied.market && target === applied.target) reload();
    else setApplied({ market, target });
  }

  const bets = data?.sure_bets || [];
  const totalStake = bets.reduce((a, b) => a + b.bankroll, 0);

  return (
    <>
      <div className="page-title">
        <div>
          <h1>Sure bets</h1>
          <p>Every open arb, sized so each match returns your target profit.</p>
        </div>
        <form className="toolbar" onSubmit={apply}>
          <label className="field">Market
            <select className="select" value={market} onChange={(e) => setMarket(e.target.value)}>
              <option value="">All markets</option>
              {Object.entries(MARKETS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label className="field">Target profit per match
            <span className="addon"><span>KES</span>
              <input className="input" type="number" min="1" inputMode="decimal" value={target} onChange={(e) => setTarget(e.target.value)} />
            </span>
          </label>
          <button className="btn" disabled={loading}><RefreshCw className={loading ? "spin" : ""} />Apply</button>
        </form>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: 16 }}><AlertCircle />{error}</div>}

      {bets.length > 0 && (
        <div className="summary-strip">
          <span><strong>{bets.length}</strong> arbs</span>
          <span>Stake for all <strong className="num">{KES(totalStake)}</strong></span>
          <span>Profit if all placed <strong className="pos num">{KES(bets.length * data.target)}</strong></span>
        </div>
      )}

      {data && !bets.length && (
        <div className="card">
          <div className="empty">
            <div className="empty-ic"><SearchX /></div>
            <h3>No open arbs{applied.market && ` for ${MARKETS[applied.market]}`}</h3>
            <p>New ones appear here after the next odds fetch and scan.</p>
          </div>
        </div>
      )}

      <div className="bets">
        {bets.map((b) => <Bet bet={b} key={`${b.match}|${b.market}|${data.target}|${b.rank}`} />)}
      </div>
    </>
  );
}
