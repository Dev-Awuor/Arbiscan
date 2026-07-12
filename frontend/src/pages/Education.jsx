import { Link } from "react-router-dom";

export default function Education() {
  return (
    <>
      <div className="page-head"><h1>Education</h1></div>
      <p className="lead">Everything you need to understand arbitrage betting and use Arbiscan well.</p>

      <section className="card explainer">
        <h2>What is arbitrage betting?</h2>
        <p>
          Arbitrage (“arbing” or a “sure bet”) means backing <strong>every</strong> outcome of an
          event across different bookmakers so that you make a profit no matter what happens.
          It exists because books disagree on prices. When their disagreement is large enough,
          the combined implied probability drops below 100% — and that gap is your guaranteed edge.
        </p>

        <h2>The maths in one line</h2>
        <p>
          For decimal odds, the <strong>implied probability</strong> of an outcome is <code>1 / odds</code>.
          Add them up across all outcomes:
        </p>
        <ul>
          <li><strong>Sum &lt; 100%</strong> → arbitrage. The smaller the sum, the bigger the profit.</li>
          <li><strong>Sum &gt; 100%</strong> → the bookmaker’s margin (“overround”/“hold”) — no edge.</li>
        </ul>
        <p>
          Profit margin ≈ <code>1 − sum</code>. Stakes are split so each outcome returns the same:
          <code> stake = bankroll × (1/odds) / sum</code>.
        </p>

        <h2>How to actually place an arb</h2>
        <ol className="steps">
          <li><strong>Find the prices</strong> — different books, same event, opposite outcomes.</li>
          <li><strong>Size the stakes</strong> with the <Link to="/">calculator</Link> (or use our live feed).</li>
          <li><strong>Place the longer-odds leg first</strong> — it’s the most likely to shorten or be limited.</li>
          <li><strong>Place the other leg(s) immediately</strong> to lock the margin before prices move.</li>
        </ol>

        <h2>Risks &amp; reality (read this)</h2>
        <ul>
          <li><strong>Odds move fast.</strong> An arb can vanish in seconds — speed matters.</li>
          <li><strong>Stake limits &amp; “gubbing.”</strong> Books may limit or void winning-side bets.</li>
          <li><strong>Both legs must land.</strong> If one bet is rejected, you’re exposed on the other.</li>
          <li><strong>Margins are thin.</strong> Real arbs are usually 0.5–3%; big numbers usually mean stale or mispriced data.</li>
        </ul>
        <p className="muted small">
          Arbiscan filters out implausible “too-good-to-be-true” arbs automatically and shows only
          realistic, sized opportunities. Bet responsibly — 18+.
        </p>
      </section>

      <section className="card cta-band">
        <div>
          <h2>Ready to stop hunting odds by hand?</h2>
          <p className="muted">Premium scans the books and hands you ready-to-place, profit-sized sure bets.</p>
        </div>
        <Link to="/pricing" className="btn btn-lg">See Premium →</Link>
      </section>
    </>
  );
}
