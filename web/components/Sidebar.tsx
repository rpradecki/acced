"use client";

import { useStore } from "@/lib/store";
import { CONNECTOR_MODE } from "@/lib/connectors";
import type { Role } from "@/lib/types";

const ROLES: [Role, string][] = [
  ["clerical", "R. Patel — Clerical / Reception"],
  ["clinical", "Dr A. Rangi — Clinician"],
  ["audit", "M. Chen — Audit / Review"],
];

export default function Sidebar() {
  const { role, setRole } = useStore();

  return (
    <aside className="sidebar">
      <h3>ACC Claim Console</h3>
      <p className="muted">Health New Zealand | Te Whatu Ora · research mockup</p>
      <hr />

      <div className="lbl">Signed in as</div>
      {ROLES.map(([key, label]) => (
        <button key={key} className="rolebtn" aria-pressed={role === key} onClick={() => setRole(key)}>
          {label}
        </button>
      ))}
      <p className="note">
        🔒 Sign-in is <b>simulated</b> (dev only). Production uses My Health Account Workforce (OIDC) via the auth
        connector.
      </p>

      <hr />
      <p className="note">
        Roles: <b>clerical</b> edits admin, views clinical, can&apos;t submit · <b>clinical</b> does all ·{" "}
        <b>audit</b> sees all claims, searchable, read-only inspect with the audit trail.
      </p>

      <details>
        <summary>Integration status (stubbed connectors)</summary>
        <div className="note">
          {Object.entries(CONNECTOR_MODE).map(([name, mode]) => (
            <div key={name}>• {name} — {mode}</div>
          ))}
        </div>
      </details>
    </aside>
  );
}
