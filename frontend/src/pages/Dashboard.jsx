import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api";
import { useAuth } from "../auth";

const KES = (n) =>
  "KES " + Number(n).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/* One sure-bet card with editable, auto-balancing stakes (like a pro arb tool). */
function SureBetCard({ bet }) {
  const inv = bet.legs.map((l) => 1 / l.odds);
  const sumInv = inv.reduce((a, b) => a + b, 0);
  const [bankroll, setBankroll] = useState(bet.bankroll);
  // "Bet first" = the longest-odds leg (most likely to move / be limited).
  const firstIdx = bet.legs.reduce((mi, l, i, a) => (l.odds > a[mi].odds ? i : mi), 0);

  const stakeOf = (i) => bankroll * (inv[i] / sumInv);
  const payout = bankroll / sumInv;
  const profit = payout - bankroll;

  // Edit one leg's stake -> rebalance the whole book to keep payouts equal.
  const editStake = (i, val) => {
    const s = parseFloat(val) || 0;
    setBankroll((s * sumInv) / inv[i]);
  };

  return (
    <div className="surebet">
      <div className="surebet-head">
        <span className="rank">#{bet.rank}</span>
        <strong className="sb-match">{bet.match}</strong>
        <span className="muted sb-market">{bet.market}</span>
        <span className="pill pos-pill">+{KES(profit).replace("KES ", "")} · {bet.margin_pct}% ROI</span>
      </div>

      {bet.legs.map((leg, i) => (
        <div className="sb-leg" key={i}>
          <div className="sb-book">{leg.book}</div>
          <div className="sb-sel">
            {leg.label} <span className="sb-odds">@ {leg.odds}</span>
            {i === firstIdx && <span className="bet-first" title="Place this leg first — longest odds, most likely to move">Bet First ⓘ</span>}
          </div>
          <label className="sb-size">Bet size
            <input type="number" min="0" value={stakeOf(i).toFixed(2)}
              onChange={(e) => editStake(i, e.target.value)} />
          </label>
          <div className="sb-payout">Payout <strong>{KES(stakeOf(i) * leg.odds)}</strong></div>
          <button className="btn btn-sm btn-ghost" title="We show the figures — place the bet at your book">Bet</button>
        </div>
      ))}

      <div className="surebet-foot">
        <span>Total stake <strong>{KES(bankroll)}</strong> → guaranteed <strong className="pos">{KES(profit)}</strong></span>
        <button className="btn btn-sm" title="Place both legs at your books to lock the profit">⚡ Place Both</button>
      </div>
    </div>
  );
}

function UpgradeTeaser({ cap, locked }) {
  return (
    <div className="teaser">
      <h2>Unlock Profitable Arbitrage Bets</h2>
      <p className="teaser-lead">
        You're seeing arbitrage opportunities up to <strong>{cap}% ROI</strong>.
        {locked > 0
          ? <> Unlock the <strong>{locked} higher-profit</strong> arb{locked > 1 ? "s" : ""} — every arb above {cap}%, plus full bet details — with Arbiscan Premium.</>
          : <> Upgrade to Premium for live, in-game arbs the moment odds move.</>}
      </p>
      <div className="teaser-tiers">
        <div className="tier">
          <div className="tier-name">CORE</div>
          <div className="tier-head">Arbs above {cap}% ROI</div>
          <p className="muted small">Unlock every higher-profit pre-game arbitrage opportunity.</p>
        </div>
        <div className="tier tier-rec">
          <span className="rec">RECOMMENDED</span>
          <div className="tier-name">PRO</div>
          <div className="tier-head">Everything in Core, plus live arbs</div>
          <p className="muted small">Catch live, in-game arbs the moment odds move during games.</p>
        </div>
      </div>
      <Link to="/pricing" className="btn btn-lg">Start Your 7-Day Free Trial</Link>
      <div className="trust">
        <span>📚 Multi-book</span><span>🏆 Tennis · NBA · MMA · World Cup</span>
        <span>🛡️ Guaranteed profit</span><span>🧮 Auto stake math</span>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { isPremium } = useAuth();
  const [target, setTarget] = useState(500);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [updated, setUpdated] = useState(null);

  async function load() {
    setLoading(true); setErr("");
    try {
      const { data } = await api.get(`/live/sure-bets/?target=${target}`);
      setData(data);
      setUpdated(new Date());
    } catch {
      setErr("Could not load the live feed.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  return (
    <>
      <div className="page-head">
        <h1>Arbitrage Bet Finder</h1>
        <span className={`tag ${isPremium ? "tag-prem" : "tag-free"}`}>{isPremium ? "PREMIUM" : "FREE preview"}</span>
      </div>

      <div className="toolbar">
        <div className="toolbar-grp">
          <span className="seg active">Arbs Only</span>
          <span className="seg">Low Hold</span>
        </div>
        <label className="inline">Target profit
          <input type="number" min="1" value={target} onChange={(e) => setTarget(e.target.value)} className="amount sm" />
        </label>
        <button className="btn btn-sm" onClick={load} disabled={loading}>↻ Refresh</button>
        <span className="muted small upd">
          {loading ? "Updating…" : updated ? `Last updated: ${updated.toLocaleTimeString()}` : ""}
        </span>
      </div>

      {err && <p className="error">{err}</p>}

      {data && !data.is_premium && <UpgradeTeaser cap={data.free_roi_cap} locked={data.locked_count} />}

      {data && data.count === 0 && !data.locked_count && (
        <div className="card"><p className="muted">No live arbs right now. Run a scan (premium pipeline), then refresh.</p></div>
      )}

      {data?.sure_bets?.map((b, i) => <SureBetCard bet={b} key={i} />)}

      {data && !data.is_premium && data.count > 0 && (
        <p className="muted small center">
          Showing {data.count} preview arb{data.count > 1 ? "s" : ""}. {data.locked_count > 0 &&
            <Link to="/pricing">Unlock {data.locked_count} more →</Link>}
        </p>
      )}
    </>
  );
}
