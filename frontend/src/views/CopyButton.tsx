import { useState } from "react";

// Copy-to-clipboard icon button. Shows a brief "Copied!" confirmation.
export default function CopyButton({ value, label = "Copy" }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      // Fallback for non-secure contexts where clipboard API is unavailable.
      const ta = document.createElement("textarea");
      ta.value = value;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <button
      type="button"
      className="copy-btn"
      onClick={copy}
      aria-label={`${label} ${value}`}
      title={label}
    >
      <span aria-hidden="true">{copied ? "✓" : "📋"}</span>
      <span>{copied ? "Copied!" : label}</span>
    </button>
  );
}
