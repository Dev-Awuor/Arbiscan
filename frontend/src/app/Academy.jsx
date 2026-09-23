import { useCallback, useEffect, useState } from "react";
import { Check, Lock, Flame, Trophy, Sparkles, ArrowRight, RotateCcw, X } from "lucide-react";
import Waves from "../Waves";
import { GOAL, RANKS, rankOf, useProgress } from "./progress";

/* ---------- question generators (all maths is the real arb maths) ---------- */
const rnd = (a, b) => a + Math.random() * (b - a);
const r2 = (x) => Math.round(x * 100) / 100;
const pick = (xs) => xs[Math.floor(Math.random() * xs.length)];
const shuffle = (xs) => xs.map((x) => [Math.random(), x]).sort((a, b) => a[0] - b[0]).map((x) => x[1]);
const BOOKS = ["Pinnacle", "Bet365", "1xBet", "Betsson", "Unibet", "Betika"];
const pct = (x) => `${(x * 100).toFixed(1)}%`;
const kes = (x) => `KES ${Math.round(x).toLocaleString("en-KE")}`;
const sumInv = (odds) => odds.reduce((a, o) => a + 1 / o, 0);

/* Odds for n outcomes whose implied total lands near `target`. */
function oddsFor(n, target) {
  const w = Array.from({ length: n }, () => rnd(0.6, 1.4));
  const tw = w.reduce((a, b) => a + b, 0);
  return w.map((x) => r2(1 / ((x / tw) * target)));
}

/* Keep options whose labels are unique, then shuffle. */
const options = (correct, distractors) =>
  shuffle([correct, ...distractors.filter((d, i, a) => d !== correct && a.indexOf(d) === i).slice(0, 3)]);

const LEVELS = [
  {
    id: "read", title: "Read the odds", icon: "1",
    lesson: "Decimal odds hide a probability. Divide 1 by the odds: 2.00 means 50%, 4.00 means 25%. That is the bookmaker's view of the chance, with their cut baked in.",
    make() {
      const o = r2(rnd(1.2, 6));
      const c = 1 / o;
      const ans = pct(c);
      return {
        prompt: <>What chance does odds of <b>{o.toFixed(2)}</b> imply?</>,
        options: options(ans, [pct(c * rnd(0.6, 0.8)), pct(Math.min(c * rnd(1.25, 1.5), 0.99)), pct(o / 10), pct(1 - c)]),
        answer: ans,
        explain: `1 ÷ ${o.toFixed(2)} = ${ans}.`,
      };
    },
  },
  {
    id: "spot", title: "Spot the arb", icon: "2",
    lesson: "Take the best price for every outcome, from any book, and add up their implied chances. Under 100% is an arb: back everything and you still profit. Over 100% is the bookmakers' margin.",
    make() {
      let odds, s;
      do {
        odds = oddsFor(pick([2, 2, 3]), Math.random() < 0.5 ? rnd(0.95, 0.99) : rnd(1.01, 1.06));
        s = sumInv(odds);
      } while (Math.abs(s - 1) < 0.004);
      const names = odds.length === 3 ? ["Home", "Draw", "Away"] : ["Player A", "Player B"];
      const books = shuffle(BOOKS);
      const ans = s < 1 ? "Arb" : "No arb";
      return {
        prompt: <>Is this an arb?<span className="q-legs">{odds.map((o, i) => <span key={i}>{names[i]} <b>{o.toFixed(2)}</b> @ {books[i]}</span>)}</span></>,
        options: ["Arb", "No arb"],
        answer: ans,
        explain: `${odds.map((o) => `1/${o.toFixed(2)}`).join(" + ")} = ${pct(s)}, which is ${s < 1 ? "under" : "over"} 100%.`,
      };
    },
  },
  {
    id: "size", title: "Size the stakes", icon: "3",
    lesson: "Split your total so every outcome returns the same amount: stake on an outcome = total × (1 ÷ odds) ÷ implied total. Longer odds get the smaller stake.",
    make() {
      let a, b;
      do { [a, b] = oddsFor(2, rnd(0.95, 0.985)); } while (Math.abs(a - b) < 0.25);
      const total = pick([1000, 2000, 5000, 10000]);
      const s = sumInv([a, b]);
      const sa = (total * (1 / a)) / s;
      const ans = kes(sa);
      return {
        prompt: <>Total stake <b>{kes(total)}</b> on Home <b>{a.toFixed(2)}</b> / Away <b>{b.toFixed(2)}</b>. How much goes on Home?</>,
        options: options(ans, [kes(total - sa), kes(total / 2), kes(sa * 1.12), kes(sa * 0.88)]),
        answer: ans,
        explain: `${kes(total)} × (1/${a.toFixed(2)}) ÷ ${pct(s)} = ${ans}. Both sides then return ${kes(sa * a)}.`,
      };
    },
  },
  {
    id: "first", title: "Place it first", icon: "4",
    lesson: "Prices move while you place bets. The longest odds move most and are the most likely to be limited, so place that leg first, then the rest straight away.",
    make() {
      let odds;
      do { odds = oddsFor(pick([2, 3]), rnd(0.95, 0.99)); } while (new Set(odds).size < odds.length);
      const books = shuffle(BOOKS);
      const labels = odds.map((o, i) => `${books[i]} @ ${o.toFixed(2)}`);
      const ans = labels[odds.indexOf(Math.max(...odds))];
      return {
        prompt: <>You have found an arb. Which leg do you place first?</>,
        options: shuffle(labels),
        answer: ans,
        explain: `${ans} has the longest odds, so it is the price most likely to move or be limited.`,
      };
    },
  },
  {
    id: "fake", title: "Too good to be true", icon: "5",
    lesson: "Real arbs are small, usually 0.5–3%. A 20% 'arb' almost always means a stale or wrong price. Arbiscan throws out anything above 15%.",
    make() {
      const real = [0, 1, 2].map(() => oddsFor(2, rnd(0.97, 0.995)));
      const fake = oddsFor(2, rnd(0.65, 0.8));
      const all = shuffle([...real, fake]);
      const label = (o) => `${o[0].toFixed(2)} / ${o[1].toFixed(2)}`;
      return {
        prompt: <>Four two-way arbs from the scanner. Which one is probably bad data?</>,
        options: all.map(label),
        answer: label(fake),
        explain: all.map((o) => `${label(o)}: ${((1 - sumInv(o)) * 100).toFixed(1)}% margin`).join(" · "),
      };
    },
  },
];

/* ---------- UI ---------- */
function LevelMap({ progress, current, onPick }) {
  return (
    <div className="lvl-map">
      <svg className="lvl-path" viewBox="0 0 1000 120" preserveAspectRatio="none" aria-hidden="true">
        <path d="M40 60 C 160 -10, 240 130, 340 60 S 540 -10, 640 60 S 840 130, 960 60" />
      </svg>
      {LEVELS.map((l, i) => {
        const done = progress.cleared.includes(l.id);
        const unlocked = i === 0 || progress.cleared.includes(LEVELS[i - 1].id);
        return (
          <button key={l.id} className={`lvl${done ? " done" : ""}${i === current ? " current" : ""}`}
            disabled={!unlocked} onClick={() => onPick(i)} aria-label={`Level ${i + 1}: ${l.title}${unlocked ? "" : " (locked)"}`}>
            <span className="lvl-dot">{done ? <Check /> : unlocked ? l.icon : <Lock />}</span>
            <span className="lvl-name">{l.title}</span>
          </button>
        );
      })}
    </div>
  );
}

export default function Academy() {
  const [progress, setProgress] = useProgress();
  const firstOpen = LEVELS.findIndex((l) => !progress.cleared.includes(l.id));
  const [level, setLevel] = useState(firstOpen === -1 ? 0 : firstOpen);
  const [q, setQ] = useState(() => LEVELS[level].make());
  const [chosen, setChosen] = useState(null);
  const [celebrate, setCelebrate] = useState(false);

  const L = LEVELS[level];
  const count = progress.correct[L.id] || 0;
  const cleared = progress.cleared.includes(L.id);

  const next = useCallback(() => { setChosen(null); setCelebrate(false); setQ(LEVELS[level].make()); }, [level]);
  useEffect(() => { next(); }, [next]);

  function answer(opt) {
    if (chosen) return;
    setChosen(opt);
    const right = opt === q.answer;
    setProgress((p) => {
      const streak = right ? p.streak + 1 : 0;
      const n = (p.correct[L.id] || 0) + (right ? 1 : 0);
      const justCleared = right && n >= GOAL && !p.cleared.includes(L.id);
      if (justCleared) setCelebrate(true);
      return {
        ...p,
        streak,
        best: Math.max(p.best, streak),
        xp: p.xp + (right ? 10 + (streak >= 3 ? 5 : 0) : 0) + (justCleared ? 50 : 0),
        correct: { ...p.correct, [L.id]: n },
        cleared: justCleared ? [...p.cleared, L.id] : p.cleared,
      };
    });
  }

  // Keyboard: 1-4 answer, Enter for next.
  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === "INPUT") return;
      const i = Number(e.key) - 1;
      if (!chosen && i >= 0 && i < q.options.length) answer(q.options[i]);
      if (chosen && e.key === "Enter") next();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const rank = rankOf(progress);
  const nextRank = RANKS[Math.min(progress.cleared.length + 1, RANKS.length - 1)];

  return (
    <>
      <section className="banner">
        <Waves className="banner-waves" />
        <div className="banner-in">
          <p className="banner-eyebrow"><Sparkles /> Arb Academy</p>
          <h1>Learn to arb, one level at a time</h1>
          <p className="banner-sub">Five short levels. Answer {GOAL} right to clear each one and earn your next rank.</p>
        </div>
        <div className="banner-stats">
          <div><span>Rank</span><strong>{rank}</strong></div>
          <div><span>XP</span><strong className="num">{progress.xp}</strong></div>
          <div><span>Streak</span><strong className="num"><Flame className={progress.streak >= 3 ? "hot" : ""} />{progress.streak}</strong></div>
        </div>
      </section>

      <LevelMap progress={progress} current={level} onPick={setLevel} />

      <div className="academy">
        <aside className="card lesson">
          <div className="card-content">
            <span className="lesson-num">Level {level + 1}</span>
            <h2>{L.title}</h2>
            <p>{L.lesson}</p>
            <div className="lvl-progress">
              <div className="lvl-progress-head"><span>Progress</span><span className="num">{Math.min(count, GOAL)} / {GOAL}</span></div>
              <div className="bar-track"><div className="bar-fill accent" style={{ width: `${(Math.min(count, GOAL) / GOAL) * 100}%` }} /></div>
            </div>
            {cleared && <p className="cleared"><Trophy /> Cleared. Keep practising for XP.</p>}
          </div>
        </aside>

        <section className="card quiz">
          {celebrate ? (
            <div className="celebrate">
              <div className="confetti" aria-hidden="true">{Array.from({ length: 18 }, (_, i) => <i key={i} style={{ "--i": i }} />)}</div>
              <Trophy className="trophy" />
              <h2>Level cleared</h2>
              <p>+50 XP. You are now <b>{rank}</b>.{level < LEVELS.length - 1 && ` Next up: ${LEVELS[level + 1].title}.`}</p>
              <div className="celebrate-actions">
                {level < LEVELS.length - 1
                  ? <button className="btn btn-accent" onClick={() => setLevel(level + 1)}>Next level<ArrowRight /></button>
                  : <p className="muted">That's every level. You are an Arb Master.</p>}
                <button className="btn btn-outline" onClick={next}><RotateCcw />Keep practising</button>
              </div>
            </div>
          ) : (
            <div className="card-content">
              <p className="q-prompt">{q.prompt}</p>
              <div className={`q-options${q.options.length === 2 ? " two" : ""}`}>
                {q.options.map((opt, i) => {
                  const state = !chosen ? "" : opt === q.answer ? " right" : opt === chosen ? " wrong" : " dim";
                  return (
                    <button key={opt} className={`q-opt${state}`} onClick={() => answer(opt)} disabled={!!chosen}>
                      <kbd>{i + 1}</kbd><span>{opt}</span>
                      {chosen && opt === q.answer && <Check className="q-mark" />}
                      {chosen && opt === chosen && opt !== q.answer && <X className="q-mark" />}
                    </button>
                  );
                })}
              </div>
              {chosen && (
                <div className={`q-feedback${chosen === q.answer ? " right" : " wrong"}`} role="status">
                  <div>
                    <strong>{chosen === q.answer ? `Correct${progress.streak >= 3 ? " · streak bonus" : ""}` : "Not quite"}</strong>
                    <p>{q.explain}</p>
                  </div>
                  {chosen === q.answer && <span className="xp-pop">+{progress.streak >= 3 ? 15 : 10} XP</span>}
                  <button className="btn" onClick={next}>Next<ArrowRight /></button>
                </div>
              )}
              {!chosen && <p className="q-hint">Press 1–{q.options.length} to answer</p>}
            </div>
          )}
        </section>
      </div>
      <p className="academy-foot">Rank after this level: <b>{nextRank}</b> · Best streak <b className="num">{progress.best}</b> · Progress is saved in this browser.</p>
    </>
  );
}
