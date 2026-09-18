import React, { useState } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./styles.css";
import Landing from "./views/Landing";
import Admin from "./views/Admin";
import Agent from "./views/Agent";
import Customer from "./views/Customer";
import Login from "./Login";
import {
  currentView,
  getRole,
  getUsername,
  isAuthenticated,
  logout,
  requiredRoleFor,
} from "./auth";

/**
 * Production entry point. Unlike the POC (client-side router across all views),
 * each subdomain serves exactly ONE view, decided by the hostname. Protected
 * views are wrapped in an auth + role gate. Authorization is still enforced by
 * the API; this gate is UX so users don't see a broken screen.
 */
function App() {
  const view = currentView();
  const [, force] = useState(0);
  const rerender = () => force((n) => n + 1);

  // Landing is public.
  if (view === "landing") {
    return <Landing />;
  }

  const needsRole = requiredRoleFor(view);

  if (!isAuthenticated()) {
    return <Login view={view} onSuccess={rerender} />;
  }

  // Authenticated but wrong role for this surface.
  const role = getRole();
  if (needsRole && role !== needsRole) {
    return (
      <div style={{ maxWidth: 420, margin: "10vh auto", fontFamily: "system-ui" }}>
        <h1 style={{ fontSize: 20 }}>Access denied</h1>
        <p>
          You are signed in as <b>{getUsername()}</b> ({role}), but this area
          requires the <b>{needsRole}</b> role.
        </p>
        <button onClick={() => { logout(); rerender(); }}>Sign in as another user</button>
      </div>
    );
  }

  const Bar = (
    <div
      style={{
        display: "flex",
        justifyContent: "flex-end",
        gap: 12,
        padding: "6px 12px",
        fontSize: 13,
        color: "#555",
        borderBottom: "1px solid #eee",
      }}
    >
      <span>
        {getUsername()} · {role}
      </span>
      <a
        href="#"
        onClick={(e) => {
          e.preventDefault();
          logout();
          rerender();
        }}
      >
        Sign out
      </a>
    </div>
  );

  let content: React.ReactNode = null;
  if (view === "admin") content = <Admin />;
  else if (view === "agent") content = <Agent />;
  else if (view === "customer") content = <Customer />;

  return (
    <>
      {Bar}
      {content}
    </>
  );
}

// Wrap in BrowserRouter: the POC view components (Landing, Page) use <Link>,
// which needs a Router context. In this production model each subdomain renders
// exactly one view, so routing itself is unused — the provider just satisfies
// the <Link> hooks. Without it, <Link> calls useContext(RouterContext) === null
// and throws "Cannot destructure property 'basename'".
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
