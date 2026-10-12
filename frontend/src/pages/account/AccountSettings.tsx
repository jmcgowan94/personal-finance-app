import { NavLink, Outlet } from "react-router-dom";

export function AccountSettings() {
  return (
    <>
      <div className="page-header">
        <h1>Account Settings</h1>
      </div>
      <div className="settings-layout">
        <nav className="nav settings-nav" aria-label="Account settings">
          <NavLink to="general">General Settings</NavLink>
          <NavLink to="information">Account Information</NavLink>
        </nav>
        <div>
          <Outlet />
        </div>
      </div>
    </>
  );
}
