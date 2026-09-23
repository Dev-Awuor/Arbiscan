import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./auth";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Shell from "./app/Shell";
import Overview from "./app/Overview";
import SureBets from "./app/SureBets";
import Calculator from "./app/Calculator";
import Academy from "./app/Academy";

function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  return user ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/app" element={<RequireAuth><Shell /></RequireAuth>}>
        <Route index element={<Overview />} />
        <Route path="sure-bets" element={<SureBets />} />
        <Route path="calculator" element={<Calculator />} />
        <Route path="academy" element={<Academy />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
