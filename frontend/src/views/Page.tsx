import { ReactNode } from "react";
import { Link } from "react-router-dom";

// Standalone page shell: header (with a panel icon) + content wrap.
export default function Page({
  title,
  icon,
  mobile,
  children,
}: {
  title: string;
  icon?: string;
  mobile?: boolean;
  children: ReactNode;
}) {
  return (
    <>
      <div className="header">
        <div className="logo">E.</div>
        {icon && <span className="panel-icon" aria-hidden="true">{icon}</span>}
        <h1>{title}</h1>
        <Link to="/" className="muted" style={{ marginLeft: "auto" }}>
          &larr; all views
        </Link>
      </div>
      <div className={`wrap ${mobile ? "mobile" : ""}`}>{children}</div>
    </>
  );
}
