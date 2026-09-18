/**
 * Production landing page (smart-locker.yeng.click).
 *
 * Unlike the POC's Landing (which renders all three views side-by-side in one
 * public page), the production landing is a plain entry/directory: it points
 * each role at its own subdomain, where the view is served behind a login +
 * role gate. There is no functional locker UI here — the operator surfaces
 * live on their subdomains, and the API enforces authorization regardless.
 */
export default function LandingProd() {
  // Derive the per-view subdomains from the current host so this works on
  // smart-locker.yeng.click (-> admin.smart-locker.yeng.click, ...) as well as
  // any other base host it's deployed under.
  const { protocol, host } = window.location;
  const sub = (name: string) => `${protocol}//${name}.${host}`;

  const cards = [
    { name: "admin", title: "Admin", icon: "🗄️", blurb: "Manage lockers and view the transaction log." },
    { name: "agent", title: "Delivery Agent", icon: "🚚", blurb: "Store incoming packages in a locker." },
    { name: "customer", title: "Customer", icon: "🙋", blurb: "Collect a package with your pickup code." },
  ];

  return (
    <>
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

      <p className="dash-hint muted">
        Choose your area. Each opens its own sign-in — access is restricted by
        role.
      </p>

      <div className="dashboard">
        {cards.map((c) => (
          <a
            key={c.name}
            href={sub(c.name)}
            className="col"
            style={{ textDecoration: "none", color: "inherit" }}
          >
            <div className="col-head">
              <div>
                <div className="col-title">
                  <span className="panel-icon" aria-hidden="true">
                    {c.icon}
                  </span>
                  {c.title}
                </div>
                <div className="muted col-sub">{c.blurb}</div>
              </div>
              <span className="col-toggle" aria-hidden="true">
                ›
              </span>
            </div>
          </a>
        ))}
      </div>
    </>
  );
}
