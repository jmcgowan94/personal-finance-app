import { useEffect, useRef, useState, type PointerEvent } from "react";
import { Link, NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AccountInformation } from "./pages/account/AccountInformation";
import { AccountSettings } from "./pages/account/AccountSettings";
import { GeneralSettings } from "./pages/account/GeneralSettings";
import { Categories } from "./pages/Categories";
import { Dashboard } from "./pages/Dashboard";
import { Import } from "./pages/Import";
import { Transactions } from "./pages/Transactions";
import { useSyncTheme } from "./lib/theme";

// Grace period so the mouse can travel from the toggle to the sidebar (and back)
// without it closing in between.
const CLOSE_DELAY_MS = 200;

function SidebarIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <rect x="2.5" y="3.5" width="15" height="13" rx="2" />
      <line x1="7.5" y1="3.5" x2="7.5" y2="16.5" />
    </svg>
  );
}

export function App() {
  useSyncTheme();
  const [open, setOpen] = useState(false);
  // "hover": opened by mouse, closes when the mouse leaves.
  // "click": opened by touch or keyboard, closes on tap outside, Escape or navigation.
  const [mode, setMode] = useState<"hover" | "click">("hover");
  const closeTimer = useRef<number | undefined>(undefined);
  const lastPointer = useRef("");
  const location = useLocation();

  const cancelClose = () => window.clearTimeout(closeTimer.current);
  useEffect(() => cancelClose, []);

  function openOnHover(e: PointerEvent) {
    if (e.pointerType !== "mouse") return;
    cancelClose();
    setMode("hover");
    setOpen(true);
  }

  function closeOnLeave(e: PointerEvent) {
    if (e.pointerType !== "mouse" || mode !== "hover") return;
    cancelClose();
    closeTimer.current = window.setTimeout(() => setOpen(false), CLOSE_DELAY_MS);
  }

  function onToggleClick() {
    // Mouse users are handled by hover; clicks only matter for touch and keyboard.
    const pointer = lastPointer.current;
    lastPointer.current = "";
    if (pointer === "mouse") return;
    setMode("click");
    setOpen((o) => !o);
  }

  useEffect(() => {
    if (mode === "click") setOpen(false);
  }, [location.pathname]); // only on navigation, not when mode changes

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  return (
    <>
      <header className="topbar">
        <div className="topbar-start">
          <button
            className="icon-button"
            aria-label={open ? "Hide menu" : "Show menu"}
            aria-expanded={open}
            aria-controls="sidebar"
            onPointerDown={(e) => (lastPointer.current = e.pointerType)}
            onPointerEnter={openOnHover}
            onPointerLeave={closeOnLeave}
            onClick={onToggleClick}
          >
            <SidebarIcon />
          </button>
          <Link to="/" className="brand">
            Personal Finance App
          </Link>
        </div>
      </header>
      <div className="layout">
        <aside
          id="sidebar"
          className="sidebar"
          hidden={!open}
          onPointerEnter={(e) => e.pointerType === "mouse" && cancelClose()}
          onPointerLeave={closeOnLeave}
        >
          <nav className="nav" aria-label="Main">
            <NavLink to="/" end>
              Dashboard
            </NavLink>
            <NavLink to="/transactions">Transactions</NavLink>
            <NavLink to="/import">Import</NavLink>
            <NavLink to="/categories">Categories</NavLink>
          </nav>
          <nav className="nav sidebar-footer" aria-label="Account">
            <NavLink to="/account">Account Settings</NavLink>
          </nav>
        </aside>
        {open && mode === "click" && <div className="scrim" onClick={() => setOpen(false)} />}
        <main>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/import" element={<Import />} />
            <Route path="/categories" element={<Categories />} />
            <Route path="/account" element={<AccountSettings />}>
              <Route index element={<Navigate to="general" replace />} />
              <Route path="general" element={<GeneralSettings />} />
              <Route path="information" element={<AccountInformation />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </>
  );
}
