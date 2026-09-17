import Page from "./Page";

// Placeholder — the delivery agent view is built in a later milestone.
export function AgentBody() {
  return (
    <div className="card">
      <h2>Store a package</h2>
      <p className="muted">Coming soon.</p>
    </div>
  );
}

export default function Agent() {
  return (
    <Page title="Delivery Agent" icon="🚚" mobile>
      <AgentBody />
    </Page>
  );
}
