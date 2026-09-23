import { useEffect, useState } from "react";

/* Academy progress lives in this browser only (per-viewer, not synced). */
const KEY = "arb-academy-v1";
export const GOAL = 5; // correct answers to clear a level
export const RANKS = ["Rookie", "Spotter", "Sizer", "Closer", "Sharp", "Arb Master"];
const EMPTY = { xp: 0, streak: 0, best: 0, cleared: [], correct: {} };

function load() {
  try { return { ...EMPTY, ...JSON.parse(localStorage.getItem(KEY)) }; } catch { return EMPTY; }
}

export function useProgress() {
  const [p, setP] = useState(load);
  useEffect(() => {
    try { localStorage.setItem(KEY, JSON.stringify(p)); } catch { /* storage blocked */ }
  }, [p]);
  return [p, setP];
}

export const rankOf = (p) => RANKS[Math.min(p.cleared.length, RANKS.length - 1)];
