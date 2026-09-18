import { useEffect, useState } from "react";
import { DemoCredential, fetchDemoCredentials } from "./auth";

/**
 * Production landing page (smart-locker.yeng.click).
 *
 * A plain entry/directory: it points each role at its own subdomain, where the
 * view is served behind a login + role gate. There is no functional locker UI
 * here — the operator surfaces live on their subdomains, and the API enforces
 * authorization regardless.
 *
 * Styling uses the app's dark theme tokens (var(--bg/panel/accent/...) defined
 * in styles.css) so this page is visually consistent with the operator views.
 * The module selection is the primary action, so it is large and emphasized.
 * Each card shows its target subdomain URL, and in REVIEW_MODE a credential
 * hint.
 */
export default function LandingProd() {
  // Derive the per-view subdomains from the current host so this works on
  // smart-locker.yeng.click (-> admin.smart-locker.yeng.click, ...) as well as
  // any other base host it's deployed under.
  const { protocol, host } = window.location;
  const subHost = (name: string) => `${name}.${host}`;
  const subUrl = (name: string) => `${protocol}//${subHost(name)}`;

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
    <>
      {/* Hover affordance for the module cards, using theme tokens. */}
      <style>{`
        .module-card {
          transition: transform .08s ease, border-color .08s ease, box-shadow .08s ease;
        }
        .module-card:hover {
          transform: translateY(-3px);
          border-color: var(--accent) !important;
          box-shadow: 0 8px 24px rgba(0,0,0,0.45);
        }
      `}</style>

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

      <div className="wrap">
        {/* Emphasized selection prompt */}
        <div style={{ textAlign: "center", margin: "8px 0 4px" }}>
          <h2 style={{ fontSize: "1.9rem", fontWeight: 800, margin: 0, color: "var(--accent)" }}>
            Choose your module
          </h2>
          <p className="muted" style={{ fontSize: "1rem", marginTop: 8 }}>
            Each module opens its own sign-in. Access is restricted by role.
          </p>
        </div>

        {/* Large, obviously-clickable module cards */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: 18,
            marginTop: 24,
          }}
        >
          {cards.map((c) => {
            const cred = creds[c.name];
            return (
              <a
                key={c.name}
                href={subUrl(c.name)}
                className="module-card"
                style={{
                  display: "block",
                  textDecoration: "none",
                  color: "var(--text)",
                  background: "var(--panel)",
                  border: "1px solid var(--border)",
                  borderRadius: 12,
                  padding: "26px 22px",
                }}
              >
                <div style={{ fontSize: 52, lineHeight: 1 }} aria-hidden="true">
                  {c.icon}
                </div>
                <div
                  style={{
                    fontSize: "1.5rem",
                    fontWeight: 800,
                    marginTop: 14,
                    color: "var(--accent)",
                  }}
                >
                  {c.title}
                </div>
                <div className="muted" style={{ fontSize: ".95rem", marginTop: 6 }}>
                  {c.blurb}
                </div>

                {/* Target URL */}
                <div
                  style={{
                    marginTop: 14,
                    fontFamily: "ui-monospace, Menlo, monospace",
                    fontSize: ".85rem",
                    color: "var(--muted)",
                    wordBreak: "break-all",
                  }}
                >
                  {subHost(c.name)}
                </div>

                {cred && (
                  <div
                    style={{
                      marginTop: 16,
                      padding: "10px 12px",
                      background: "var(--panel-2)",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      fontSize: ".85rem",
                    }}
                  >
                    <div style={{ fontWeight: 700, marginBottom: 4, color: "var(--text)" }}>
                      🔎 Reviewer login
                    </div>
                    <div style={{ fontFamily: "ui-monospace, Menlo, monospace" }}>
                      <div>
                        user: <b style={{ color: "var(--accent)" }}>{cred.username}</b>
                      </div>
                      <div>
                        pass: <b style={{ color: "var(--accent)" }}>{cred.password}</b>
                      </div>
                    </div>
                  </div>
                )}

                <div
                  style={{
                    marginTop: 18,
                    color: "var(--accent)",
                    fontWeight: 700,
                    fontSize: ".95rem",
                  }}
                >
                  Open {c.title} →
                </div>
              </a>
            );
          })}
        </div>
      </div>
    </>
  );
}
