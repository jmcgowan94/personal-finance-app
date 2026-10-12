import { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { UserMenu } from "./components/UserMenu";
import { Account } from "./pages/Account";
import { Categories } from "./pages/Categories";
import { Dashboard } from "./pages/Dashboard";
import { Import } from "./pages/Import";
import { Transactions } from "./pages/Transactions";

const NARROW = "(max-width: 800px)";
const SIDEBAR_KEY = "sidebar-open";

function useIsNarrow() {
  const [narrow, setNarrow] = useState(() => window.matchMedia(NARROW).matches);
  useEffect(() => {
    const mq = window.matchMedia(NARROW);
    const onChange = () => setNarrow(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return narrow;
}

/** Desktop remembers the viewer's choice; small screens start closed. */
function initialSidebarOpen(): boolean {
  if (window.matchMedia(NARROW).matches) return false;
  try {
    return localStorage.getItem(SIDEBAR_KEY) !== "false";
  } catch {
    return true;
  }
}

function SidebarIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <rect x="2.5" y="3.5" width="15" height="13" rx="2" />
      <line x1="7.5" y1="3.5" x2="7.5" y2="16.5" />
    </svg>
  );
}

export function App() {
  const narrow = useIsNarrow();
  const [open, setOpen] = useState(initialSidebarOpen);
  const location = useLocation();

  // On small screens the sidebar covers the page, so close it after navigating.
  useEffect(() => {
    if (narrow) setOpen(false);
  }, [location.pathname, narrow]);

  function toggle() {
    const next = !open;
    setOpen(next);
    if (!narrow) {
      try {
        localStorage.setItem(SIDEBAR_KEY, String(next));
      } catch {
        // Storage unavailable (e.g. private mode); the choice just isn't remembered.
      }
    }
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-start">
          <button
            className="icon-button"
            aria-label={open ? "Hide menu" : "Show menu"}
            title={open ? "Hide menu" : "Show menu"}
            aria-expanded={open}
            aria-controls="sidebar"
            onClick={toggle}
          >
            <SidebarIcon />
          </button>
          <Link to="/" className="brand">
            Personal Finance App
          </Link>
        </div>
        <UserMenu />
      </header>
      <div className="layout">
        <aside id="sidebar" className="sidebar" hidden={!open}>
          <nav className="nav" aria-label="Main">
            <NavLink to="/" end>
              Dashboard
            </NavLink>
            <NavLink to="/transactions">Transactions</NavLink>
            <NavLink to="/import">Import</NavLink>
            <NavLink to="/categories">Categories</NavLink>
          </nav>
        </aside>
        {open && narrow && <div className="scrim" onClick={() => setOpen(false)} />}
        <main>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/import" element={<Import />} />
            <Route path="/categories" element={<Categories />} />
            <Route path="/account" element={<Account />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </>
  );
}
