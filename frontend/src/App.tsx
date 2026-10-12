import { NavLink, Navigate, Route, Routes } from "react-router-dom";

import { Categories } from "./pages/Categories";
import { Dashboard } from "./pages/Dashboard";
import { Import } from "./pages/Import";
import { Transactions } from "./pages/Transactions";

export function App() {
  return (
    <>
      <header className="topbar">
        <span className="brand">Personal Finance</span>
        <nav className="nav">
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/transactions">Transactions</NavLink>
          <NavLink to="/import">Import</NavLink>
          <NavLink to="/categories">Categories</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/import" element={<Import />} />
          <Route path="/categories" element={<Categories />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
