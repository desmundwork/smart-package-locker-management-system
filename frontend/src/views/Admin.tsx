import Page from "./Page";

// Placeholder — the master system view is built in a later milestone.
export function AdminBody() {
  return (
    <div className="card">
      <h2>Master System View</h2>
      <p className="muted">Coming soon.</p>
    </div>
  );
}

export default function Admin() {
  return (
    <Page title="Master System View" icon="🗄️">
      <AdminBody />
    </Page>
  );
}
