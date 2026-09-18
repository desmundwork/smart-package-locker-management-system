import { useEffect, useState } from "react";
import { DemoCredential, fetchDemoCredentials } from "./auth";

/**
 * Production landing page (smart-locker.yeng.click).
 *
 * Unlike the POC's Landing (which renders all three views side-by-side in one
 * public page), the production landing is a plain entry/directory: it points
 * each role at its own subdomain, where the view is served behind a login +
 * role gate. There is no functional locker UI here — the operator surfaces
 * live on their subdomains, and the API enforces authorization regardless.
 *
 * The module/role selection is the primary action, so it is large and
 * emphasized. In REVIEW_MODE a small credential hint is shown per module.
 */
export default function LandingProd() {
  // Derive the per-view subdomains from the current host so this works on
  // smart-locker.yeng.click (-> admin.smart-locker.yeng.click, ...) as well as
  // any other base host it's deployed under.
  const { protocol, host } = window.location;
  const sub = (name: string) => `${protocol}//${name}.${host}`;

  const [creds, setCreds] = useState<Record<string, DemoCredential>>({});

  useEffect(() => {
    fetchDemoCredentials().then((res) => {
      if (!res.review_mode) return;
      const byView: Record<string, DemoCredential> = {};
      for (const c of res.credentials) byView[c.view] = c;
      setCreds(byView);
    });
  }, []);

  const cards = [
    { name: "admin", title: "Admin", icon: "🗄️", blurb: "Manage lockers and view the transaction log." },
    { name: "agent", title: "Delivery Agent", icon: "🚚", blurb: "Store incoming packages in a locker." },
    { name: "customer", title: "Customer", icon: "🙋", blurb: "Collect a package with your pickup code." },
  ];

  return (
    <div style={{ fontFamily: "system-ui", maxWidth: 1100, margin: "0 auto", padding: "0 16px" }}>
      <div className="header">
        <div className="logo">E.</div>
        <h1>Smart Package Locker Management System</h1>
        <a
          href="/docs"
          target="_blank"
          rel="noreferrer"
          className="muted"
          style={{ marginLeft: "auto" }}
        >
          API docs
        </a>
      </div>

      {/* Emphasized selection prompt */}
      <div style={{ textAlign: "center", margin: "32px 0 8px" }}>
        <h2 style={{ fontSize: 30, fontWeight: 800, margin: 0 }}>Choose your module</h2>
        <p style={{ color: "#666", fontSize: 16, marginTop: 8 }}>
          Each module opens its own sign-in. Access is restricted by role.
        </p>
      </div>

      {/* Large, obviously-clickable module cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: 20,
          marginTop: 24,
        }}
      >
        {cards.map((c) => {
          const cred = creds[c.name];
          return (
            <a
              key={c.name}
              href={sub(c.name)}
              style={{
                display: "block",
                textDecoration: "none",
                color: "inherit",
                border: "2px solid #e2e6ee",
                borderRadius: 16,
                padding: "28px 24px",
                background: "#fff",
                boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
                transition: "transform .08s ease, border-color .08s ease, box-shadow .08s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-3px)";
                e.currentTarget.style.borderColor = "#3b82f6";
                e.currentTarget.style.boxShadow = "0 8px 24px rgba(59,130,246,0.15)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "none";
                e.currentTarget.style.borderColor = "#e2e6ee";
                e.currentTarget.style.boxShadow = "0 1px 3px rgba(0,0,0,0.06)";
              }}
            >
              <div style={{ fontSize: 56, lineHeight: 1 }} aria-hidden="true">
                {c.icon}
              </div>
              <div style={{ fontSize: 24, fontWeight: 800, marginTop: 14 }}>{c.title}</div>
              <div style={{ color: "#666", fontSize: 15, marginTop: 6 }}>{c.blurb}</div>

              {cred && (
                <div
                  style={{
                    marginTop: 16,
                    padding: "10px 12px",
                    background: "#f0f6ff",
                    border: "1px solid #d6e4ff",
                    borderRadius: 10,
                    fontSize: 13,
                    fontFamily: "ui-monospace, Menlo, monospace",
                  }}
                >
                  <div style={{ fontFamily: "system-ui", fontWeight: 700, marginBottom: 4 }}>
                    🔎 Reviewer login
                  </div>
                  <div>user: <b>{cred.username}</b></div>
                  <div>pass: <b>{cred.password}</b></div>
                </div>
              )}

              <div style={{ marginTop: 18, color: "#3b82f6", fontWeight: 700, fontSize: 15 }}>
                Open {c.title} →
              </div>
            </a>
          );
        })}
      </div>
    </div>
  );
}
