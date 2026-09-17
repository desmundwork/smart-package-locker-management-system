import Page from "./Page";

// Placeholder — the customer pickup view is built in a later milestone.
export function CustomerBody() {
  return (
    <div className="card">
      <h2>Collect your package</h2>
      <p className="muted">Coming soon.</p>
    </div>
  );
}

export default function Customer() {
  return (
    <Page title="Customer Pickup" icon="🙋" mobile>
      <CustomerBody />
    </Page>
  );
}
