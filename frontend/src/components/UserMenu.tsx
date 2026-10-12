import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

function UserIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <circle cx="10" cy="10" r="8" />
      <circle cx="10" cy="8" r="2.75" />
      <path d="M4.9 15.6c1.1-1.9 2.9-2.9 5.1-2.9s4 1 5.1 2.9" />
    </svg>
  );
}

export function UserMenu() {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const firstItemRef = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    if (!open) return;
    firstItemRef.current?.focus();
    function onPointerDown(e: PointerEvent) {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div className="menu-root" ref={rootRef}>
      <button
        ref={buttonRef}
        className="icon-button"
        aria-label="User menu"
        title="User menu"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <UserIcon />
      </button>
      {open && (
        <div className="menu" role="menu">
          <Link ref={firstItemRef} to="/account" role="menuitem" onClick={() => setOpen(false)}>
            Account
          </Link>
        </div>
      )}
    </div>
  );
}
