import { Link } from "react-router-dom";
import { Zap, TrendingUp, CalendarClock, Building2, RefreshCw, ArrowRight, AlertCircle, SearchX, GraduationCap } from "lucide-react";
import Waves from "../Waves";
import { useAuth } from "../auth";
import { rankOf, useProgress } from "./progress";
import { useApi } from "../api";
import { MARKETS, ago } from "../format";

const REFRESH_CMD = `python manage.py fetch_odds --leagues all --books pinnacle bet365 1xbet betsson unibet betika
python manage.py scan_arbs`;

function Stat({ icon: Icon, label, value, sub, loading, tone = "blue" }) {
  return (
    <div className="card stat">
      <div className="card-header">{label}<span className={`stat-ic ${tone}`}><Icon /></span></div>
      <div className="card-content">
        {loading ? <div className="skeleton" style={{ height: 34, width: "60%" }} /> : <div className="stat-value">{value}</div>}
        <p className="stat-sub">{sub}</p>
      </div>
    </div>
  );
}

function Bars({ rows }) {
  const max = Math.max(1, ...rows.map((r) => r.n));
  if (!rows.length) return <p className="muted">Nothing yet.</p>;
  return (
    <div className="bars">
      {rows.map((r, i) => (
        <div className="bar-row" key={r.label}>
          <span>{r.label}</span>
          <div className="bar-track"><div className={`bar-fill${i === 0 ? " accent" : ""}`} style={{ width: `${(r.n / max) * 100}%` }} /></div>
          <span>{r.n}</span>
        </div>
      ))}
    </div>
  );
}

export default function Overview() {
  const stats = useApi("/stats/");
  const top = useApi("/live/sure-bets/?target=500");
  const s = stats.data;
  const loading = stats.loading && !s;
  const bets = top.data?.sure_bets?.slice(0, 6) || [];
  const { user } = useAuth();
  const [progress] = useProgress();

  return (
    <>
      <section className="banner">
        <Waves className="banner-waves" />
        <div className="banner-in">
          <p className="banner-eyebrow">Overview</p>
          <h1>Hi {user.username}, {s?.arbs ? <>there {s.arbs === 1 ? "is" : "are"} <span className="hl">{s.arbs} open arb{s.arbs === 1 ? "" : "s"}</span></> : "no open arbs yet"}</h1>
          <p className="banner-sub">Open arbitrage and the state of the odds pipeline.</p>
          <div className="banner-actions">
            <Link to="/app/sure-bets" className="btn btn-accent">View sure bets<ArrowRight /></Link>
            <button className="btn btn-glass" onClick={() => { stats.reload(); top.reload(); }} disabled={stats.loading}>
              <RefreshCw className={stats.loading ? "spin" : ""} />Refresh
            </button>
          </div>
        </div>
        <Link to="/app/academy" className="banner-card">
          <GraduationCap />
          <span>Academy rank</span>
          <strong>{rankOf(progress)}</strong>
          <em className="num">{progress.xp} XP · {progress.cleared.length}/5 levels</em>
        </Link>
      </section>

      {stats.error && <div className="alert alert-error" style={{ marginBottom: 16 }}><AlertCircle />{stats.error}</div>}

      <div className="stats">
        <Stat icon={Zap} label="Open arbs" loading={loading} value={s?.arbs ?? 0} sub="on fixtures that haven't started" />
        <Stat icon={TrendingUp} tone="orange" label="Best margin" loading={loading}
          value={s?.best_margin != null ? `${s.best_margin.toFixed(2)}%` : "–"}
          sub={s?.avg_margin != null ? `Average ${s.avg_margin.toFixed(2)}%` : "No arbs to average"} />
        <Stat icon={CalendarClock} label="Upcoming fixtures" loading={loading} value={s?.fixtures ?? 0}
          sub={`${(s?.odds_rows ?? 0).toLocaleString()} odds rows stored`} />
        <Stat icon={Building2} tone="orange" label="Bookmakers" loading={loading} value={s?.books?.length ?? 0} sub="with prices on upcoming fixtures" />
      </div>

      <div className="grid-main">
        <div className="card">
          <div className="card-header">
            <div><h2 className="card-title">Top arbs</h2><p className="card-desc">Highest margins right now, sized to KES 500 profit.</p></div>
            <Link to="/app/sure-bets" className="btn btn-outline btn-sm">View all<ArrowRight /></Link>
          </div>
          <div className="card-content" style={{ padding: "12px 0 8px" }}>
            {bets.length ? (
              <div className="table-wrap">
                <table className="table">
                  <thead><tr><th>Match</th><th>Market</th><th>Books</th><th className="r">Stake</th><th className="r">Margin</th></tr></thead>
                  <tbody>
                    {bets.map((b) => (
                      <tr key={b.rank}>
                        <td className="cell-main">{b.match}</td>
                        <td><span className="badge badge-secondary">{MARKETS[b.market] || b.market}</span></td>
                        <td className="cell-sub">{[...new Set(b.legs.map((l) => l.book))].join(" · ")}</td>
                        <td className="r">KES {Math.round(b.bankroll).toLocaleString()}</td>
                        <td className="r"><span className="badge badge-positive">+{b.margin_pct.toFixed(2)}%</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty">
                <div className="empty-ic"><SearchX /></div>
                <h3>{top.loading ? "Loading…" : "No open arbs"}</h3>
                {!top.loading && <p>Fetch fresh odds and run a scan to fill this list.</p>}
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header"><div><h2 className="card-title">Pipeline</h2><p className="card-desc">Where the numbers come from.</p></div></div>
          <div className="card-content">
            <dl className="kv">
              <div><dt>Last odds fetch</dt><dd>{ago(s?.last_fetch)}</dd></div>
              <div><dt>Last scan</dt><dd>{ago(s?.last_scan)}</dd></div>
              <div><dt>Odds rows (upcoming)</dt><dd className="num">{(s?.odds_rows ?? 0).toLocaleString()}</dd></div>
            </dl>
            <div className="chips" style={{ marginTop: 16 }}>
              {(s?.books || []).map((b) => <span className="badge" key={b}>{b}</span>)}
            </div>
            <pre className="cmd mono">{REFRESH_CMD}</pre>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header"><div><h2 className="card-title">Arbs by market</h2><p className="card-desc">Where the gaps are showing up.</p></div></div>
          <div className="card-content"><Bars rows={(s?.by_market || []).map((m) => ({ label: MARKETS[m.market] || m.market, n: m.n }))} /></div>
        </div>
        <div className="card">
          <div className="card-header"><div><h2 className="card-title">Arbs by bookmaker</h2><p className="card-desc">Books appearing in at least one leg.</p></div></div>
          <div className="card-content"><Bars rows={(s?.by_book || []).map((b) => ({ label: b.book, n: b.n }))} /></div>
        </div>
      </div>
    </>
  );
}
