import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Radar, Scale, HandCoins, Timer, ShieldAlert, Ban } from "lucide-react";
import { useAuth } from "../auth";
import Waves from "../Waves";
import "./landing.css";

const fmt = (n) => Math.round(n).toLocaleString("en-KE");

/* Two prices from two books. Pure client-side math, same formula as the backend. */
function BetSlip() {
  const [a, setA] = useState("2.10");
  const [b, setB] = useState("2.10");
  const [stake, setStake] = useState("10000");
  const oa = parseFloat(a), ob = parseFloat(b), s = parseFloat(stake) || 0;
  const valid = oa > 1 && ob > 1;
  const sum = valid ? 1 / oa + 1 / ob : 1;
  const isArb = valid && sum < 1;
  const sa = valid ? (s * (1 / oa)) / sum : 0;
  const sb = s - sa;
  const profit = valid ? s / sum - s : 0;
  const fill = Math.min(sum * 100, 115);

  return (
    <div className="slip">
      <div className="slip-head"><span>Bet slip</span><span className="slip-dot" /></div>
      {[["Player A", "Book 1", a, setA, sa], ["Player B", "Book 2", b, setB, sb]].map(([who, book, v, set, st]) => (
        <div className="slip-row" key={who}>
          <div>
            <strong>{who}</strong>
            <span>{book} · stake KES {fmt(st)}</span>
          </div>
          <input type="number" step="0.01" min="1.01" inputMode="decimal" value={v}
            aria-label={`${who} odds`} onChange={(e) => set(e.target.value)} />
        </div>
      ))}
      <label className="slip-stake">Total stake
        <span><em>KES</em><input type="number" min="0" inputMode="decimal" value={stake} onChange={(e) => setStake(e.target.value)} /></span>
      </label>
      <div className="meter" aria-hidden="true">
        <div className={`meter-fill${isArb ? " ok" : ""}`} style={{ width: `${(fill / 115) * 100}%` }} />
        <div className="meter-mark" style={{ left: `${(100 / 115) * 100}%` }} />
      </div>
      <p className="meter-cap">Implied total {valid ? (sum * 100).toFixed(1) : "–"}% <span>· under 100% is an arb</span></p>
      <div className={`slip-result${isArb ? " win" : ""}`} aria-live="polite">
        {isArb ? (
          <><strong>+KES {fmt(profit)}</strong><span>whoever wins</span></>
        ) : (
          <><strong>No arb yet</strong><span>push one of the odds up</span></>
        )}
      </div>
    </div>
  );
}

export default function Landing() {
  const { user } = useAuth();
  const cta = user ? { to: "/app", label: "Open dashboard" } : { to: "/register", label: "Start finding arbs" };

  return (
    <div className="lp">
      <header className="hero">
        <Waves className="hero-waves" />
        <nav className="lp-nav">
          <Link to="/" className="lp-logo"><span className="lp-mark" />arbiscan</Link>
          <div className="lp-links">
            <a href="#try">Try it</a>
            <a href="#how">How it works</a>
            <a href="#risks">Risks</a>
          </div>
          <div className="lp-right">
            {!user && <Link to="/login" className="lp-login">Log in</Link>}
            <Link to={cta.to} className="pill pill-white">{user ? "Dashboard" : "Get started"} <ArrowRight size={16} /></Link>
          </div>
        </nav>

        <div className="hero-in">
          <h1>Back every side.<br /><span className="hl">Still win.</span></h1>
          <p className="hero-sub">
            When bookmakers disagree on a price, you can bet on every outcome and still come out ahead.
            Arbiscan finds those matches and tells you exactly how much to put on each side.
          </p>
          <div className="hero-ctas">
            <Link to={cta.to} className="pill pill-accent pill-lg">{cta.label} <ArrowRight size={18} /></Link>
            <a href="#try" className="pill pill-ghost pill-lg">Try the maths</a>
          </div>
          <span className="float f1">2.10 @ Book 1</span>
          <span className="float f2">2.10 @ Book 2</span>
          <span className="float f3">+5% locked</span>
          <dl className="hero-stats">
            <div><dt>11</dt><dd>bookmakers compared</dd></div>
            <div><dt>6</dt><dd>markets scanned</dd></div>
            <div><dt>17</dt><dd>football leagues</dd></div>
            <div><dt>KES 0</dt><dd>to sign up</dd></div>
          </dl>
        </div>
      </header>

      <section id="try" className="try">
        <div className="lp-wrap try-grid">
          <div>
            <p className="eyebrow">Try it</p>
            <h2>Two prices.<br />One sure thing.</h2>
            <p className="lp-lead">
              Change the odds and watch the bar. When the implied total drops under 100%, the stakes
              below pay the same amount whichever player wins. That gap is your profit.
            </p>
            <p className="lp-lead">Arbiscan does this across every match and bookmaker it tracks, so you don't have to.</p>
          </div>
          <BetSlip />
        </div>
      </section>

      <section id="how" className="how">
        <div className="lp-wrap">
          <p className="eyebrow center">How it works</p>
          <h2 className="center">Three steps, most of them ours</h2>
          <div className="steps">
            <article><span className="step-ic"><Radar size={26} /></span><h3>We pull the prices</h3>
              <p>Odds for upcoming matches come in from each bookmaker. Matches that have already started are dropped.</p></article>
            <article><span className="step-ic"><Scale size={26} /></span><h3>We find the gaps</h3>
              <p>Every combination of books is checked for each market. Suspiciously large margins are thrown out as bad data.</p></article>
            <article className="step-hot"><span className="step-ic"><HandCoins size={26} /></span><h3>You place the bets</h3>
              <p>Each arb comes with stakes sized to the profit you want. Place the longer-odds leg first.</p></article>
          </div>
        </div>
      </section>

      <section id="risks" className="risks">
        <div className="lp-wrap">
          <p className="eyebrow center">The fine print, in plain words</p>
          <h2 className="center">What can go wrong</h2>
          <div className="risk-grid">
            <div><Timer size={22} /><h3>Prices move</h3><p>An arb can close in seconds. Check the price at the book before you stake.</p></div>
            <div><Ban size={22} /><h3>Books push back</h3><p>Bookmakers may limit stakes or restrict accounts that win consistently.</p></div>
            <div><ShieldAlert size={22} /><h3>Every leg must land</h3><p>If one bet is rejected, the others are exposed. Place them one after another.</p></div>
          </div>
        </div>
      </section>

      <section className="lp-wrap">
        <div className="cta-block">
          <Waves className="cta-waves" />
          <div className="cta-in">
            <h2>See today's arbs</h2>
            <p>Make an account and the full list opens up. No card, no trial, nothing to pay.</p>
            <Link to={cta.to} className="pill pill-accent pill-lg">{cta.label} <ArrowRight size={18} /></Link>
          </div>
          <span className="sticker">free<br />for now</span>
        </div>
      </section>

      <footer className="lp-foot">
        <Waves className="foot-waves" />
        <div className="lp-wrap foot-in">
          <div>
            <Link to="/" className="lp-logo dark"><span className="lp-mark" />arbiscan</Link>
            <p>Cross-bookmaker arbitrage, found and sized for you.</p>
          </div>
          <div className="foot-links">
            <Link to="/login">Log in</Link>
            <Link to="/register">Sign up</Link>
            <a href="#how">How it works</a>
          </div>
          <p className="foot-fine">18+. Bet responsibly. Odds change quickly; confirm every price with the bookmaker.</p>
        </div>
      </footer>
    </div>
  );
}
