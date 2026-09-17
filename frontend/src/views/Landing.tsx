import { ReactNode, useState } from "react";
import { Link } from "react-router-dom";
import { AdminBody } from "./Admin";
import { AgentBody } from "./Agent";
import { CustomerBody } from "./Customer";

// One collapsible column. Collapsed = a thin vertical strip that reclaims
// horizontal space; the label rotates to read bottom-to-top.
function Column({
  title,
  icon,
  subtitle,
  children,
}: {
  title: string;
  icon: string;
  subtitle: string;
  children: ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(false);

  if (collapsed) {
    return (
      <div className="col collapsed" onClick={() => setCollapsed(false)} title="Expand">
        <button className="col-toggle" aria-label={`Expand ${title}`}>›</button>
        <span className="col-strip-label"><span aria-hidden="true">{icon}</span> {title}</span>
      </div>
    );
  }

  return (
    <div className="col">
      <div className="col-head">
        <div>
          <div className="col-title"><span className="panel-icon" aria-hidden="true">{icon}</span>{title}</div>
          <div className="muted col-sub">{subtitle}</div>
        </div>
        <button className="col-toggle" onClick={() => setCollapsed(true)} aria-label={`Collapse ${title}`}>
          ‹
        </button>
      </div>
      <div className="col-body">{children}</div>
    </div>
  );
}

export default function Landing() {
  return (
    <>
      <div className="header">
        <div className="logo">E.</div>
        <h1>Smart Package Locker Management System</h1>
        <a href="/docs" target="_blank" rel="noreferrer" className="muted" style={{ marginLeft: "auto" }}>API docs</a>
      </div>
      <p className="dash-hint muted">
        All three views side by side. Collapse any column (‹) to reclaim space; click a collapsed strip to expand.
        Open a single view full-screen: <Link to="/admin">admin</Link> · <Link to="/agent">agent</Link> · <Link to="/customer">customer</Link>.
      </p>
      <div className="dashboard">
        <Column title="Master System View" icon="🗄️" subtitle="desktop · manage lockers + log">
          <AdminBody />
        </Column>
        <Column title="Delivery Agent" icon="🚚" subtitle="mobile · store packages">
          <AgentBody />
        </Column>
        <Column title="Customer" icon="🙋" subtitle="mobile · collect packages">
          <CustomerBody />
        </Column>
      </div>
    </>
  );
}
