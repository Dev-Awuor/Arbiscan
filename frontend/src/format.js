export const KES = (n) =>
  "KES " + Number(n).toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export const MARKETS = {
  FT_1X2: "Match result (1X2)",
  H2H: "Match winner",
  BTTS: "Both teams to score",
  OU15: "Over/Under 1.5 goals",
  OU25: "Over/Under 2.5 goals",
  OU35: "Over/Under 3.5 goals",
  DC: "Double chance",
};

export const kickoff = (iso) =>
  iso
    ? new Date(iso).toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })
    : "";

export function ago(iso) {
  if (!iso) return "never";
  const s = Math.round((Date.now() - new Date(iso)) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
}
