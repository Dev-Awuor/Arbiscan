import { Routes, Route, Link, NavLink } from "react-router-dom";
import { useAuth } from "./auth";
import Calculator from "./pages/Calculator";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Pricing from "./pages/Pricing";
import Education from "./pages/Education";

function Sidebar() {
  const item = ({ isActive }) => "side-link" + (isActive ? " active" : "");
  return (
    <aside className="sidebar">
      <Link to="/" className="brand">
        <span className="brand-mark">AS</span>
        <span className="brand-text">ARBISCAN</span>
      </Link>
      <nav>
        <NavLink to="/" end className={item}>🧮 Calculator</NavLink>
        <NavLink to="/live" className={item}>⚡ Live Sure-Bets</NavLink>
        <NavLink to="/pricing" className={item}>💎 Pricing</NavLink>
        <NavLink to="/education" className={item}>🎓 Education</NavLink>
      </nav>
      <div className="side-foot">
        <div className="side-stat"><b>110+</b> books tracked*</div>
        <div className="side-stat"><b>Guaranteed</b> profit math</div>
        <p className="side-note">*roadmap target — see Education</p>
      </div>
    </aside>
  );
}

function Topbar() {
  const { user, isPremium, logout } = useAuth();
  return (
    <header className="topbar">
      <div className="topbar-title">Arbitrage Toolkit</div>
      <div className="topbar-right">
        {user ? (
          <>
            <span className={`badge ${isPremium ? "badge-prem" : "badge-free"}`}>
              {isPremium ? "PREMIUM" : "FREE"}
            </span>
            <span className="user">{user.username}</span>
            <button className="link-btn" onClick={logout}>Log out</button>
          </>
        ) : (
          <>
            <Link to="/login" className="btn btn-ghost btn-sm">Log In</Link>
            <Link to="/register" className="btn btn-sm">Sign Up</Link>
          </>
        )}
      </div>
    </header>
  );
}

export default function App() {
  return (
    <div className="shell">
      <Sidebar />
      <div className="main">
        <Topbar />
        <div className="content">
          <Routes>
            <Route path="/" element={<Calculator />} />
            <Route path="/live" element={<Dashboard />} />
            <Route path="/pricing" element={<Pricing />} />
            <Route path="/education" element={<Education />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
          </Routes>
        </div>
        <footer className="foot">
          Arbiscan · Free arbitrage calculator · Premium live sure-bets · Bet responsibly (18+)
        </footer>
      </div>
    </div>
  );
}
