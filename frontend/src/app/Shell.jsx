import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { LayoutDashboard, Zap, Calculator, GraduationCap, LogOut, Moon, Sun, PanelLeft } from "lucide-react";
import { useAuth } from "../auth";
import "./app.css";

const NAV = [
  { to: "/app", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/app/sure-bets", label: "Sure bets", icon: Zap },
  { to: "/app/calculator", label: "Calculator", icon: Calculator },
];
const TITLES = { "/app": "Overview", "/app/sure-bets": "Sure bets", "/app/calculator": "Calculator", "/app/academy": "Academy" };

function initialTheme() {
  try {
    const t = localStorage.getItem("theme");
    if (t) return t;
  } catch { /* storage blocked */ }
  return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function Shell() {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();
  const [theme, setTheme] = useState(initialTheme);
  const [open, setOpen] = useState(false);

  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    try { localStorage.setItem("theme", theme); } catch { /* storage blocked */ }
  }, [theme]);

  const link = ({ isActive }) => "sb-link" + (isActive ? " active" : "");

  return (
    <div className={`app${open ? " nav-open" : ""}`} data-theme={theme}>
      <aside className="sidebar">
        <div className="sb-brand">
          <span className="sb-logo"><span /></span>
          <div>Arbiscan<small>Arbitrage workspace</small></div>
        </div>
        <nav className="sb-group">
          <div className="sb-label">Workspace</div>
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={link}><Icon />{label}</NavLink>
          ))}
        </nav>
        <nav className="sb-group">
          <div className="sb-label">Learn</div>
          <NavLink to="/app/academy" className={link}><GraduationCap />Academy</NavLink>
        </nav>
        <div className="sb-foot">
          <div className="sb-user">
            <span className="avatar">{user.username.slice(0, 2)}</span>
            <div><strong>{user.username}</strong><span>{user.email || "No email set"}</span></div>
            <button className="btn btn-ghost btn-icon btn-sm" onClick={logout} aria-label="Log out" title="Log out"><LogOut /></button>
          </div>
        </div>
      </aside>
      <div className="scrim" onClick={() => setOpen(false)} />

      <div className="main">
        <header className="topbar">
          <button className="btn btn-ghost btn-icon btn-sm menu-btn" onClick={() => setOpen(true)} aria-label="Open navigation"><PanelLeft /></button>
          <span className="vsep menu-btn" />
          <div className="crumbs">Arbiscan <span>/</span> <strong>{TITLES[pathname] || "Overview"}</strong></div>
          <div className="topbar-right">
            <button className="btn btn-ghost btn-icon btn-sm" aria-label="Toggle theme"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
              {theme === "dark" ? <Sun /> : <Moon />}
            </button>
          </div>
        </header>
        <main className="content"><Outlet /></main>
      </div>
    </div>
  );
}
