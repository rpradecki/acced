"use client";

import { useState } from "react";
import { useStore } from "@/lib/store";
import type { Claim } from "@/lib/types";
import { auth, persistence } from "@/lib/connectors";
import { Card, StatusPill } from "./ui";
import { Summary } from "./ReviewPanel";

export function AuditDashboard() {
  const { claims, openClaim } = useStore();
  const [q, setQ] = useState("");

  const ql = q.trim().toLowerCase();
  const filtered = ql
    ? claims.filter(
        (c) =>
          `${c.patient.given} ${c.patient.family}`.toLowerCase().includes(ql) ||
          (c.patient.nhi || "").toLowerCase().includes(ql),
      )
    : claims;

  return (
    <>
      <div className="apphdr">
        <span className="brand">
          Health New Zealand <span style={{ fontWeight: 400, opacity: 0.75 }}>| Te Whatu Ora</span>
        </span>
        <span className="sub">ACC Claim Console · Audit / Review</span>
        <span className="grow" />
        <span className="sub">{auth.currentUser("audit").name} · Audit</span>
      </div>

      <div>
        <h4>Audit · all ACC submissions</h4>
        <p className="lede">
          Search across <b>all</b> ACC45 referrals regardless of status or author. Inspect gives a read-only summary
          and the attributed audit trail.
        </p>
      </div>

      <div className="field">
        <label>Search by patient name or NHI</label>
        <input type="text" value={q} placeholder="e.g. Faleolo or NBW7712" onChange={(e) => setQ(e.target.value)} />
      </div>

      <section className="panel">
        <div className="panelhdr">All submissions · {filtered.length}</div>
        <div className="panel-body">
          {filtered.length === 0 ? (
            <p className="caption">No matching claims.</p>
          ) : (
            <div>
              <div className="claimrow audit head">
                <span>ACC45 no.</span>
                <span>Patient</span>
                <span>NHI</span>
                <span>Status</span>
                <span>Created by</span>
                <span />
              </div>
              {filtered.map((c) => (
                <div className="claimrow audit" key={c.id}>
                  <span className="ref">{c.reference}</span>
                  <span>{c.patient.given} {c.patient.family}</span>
                  <span className="mono">{c.patient.nhi || "—"}</span>
                  <span><StatusPill status={c.status} /></span>
                  <span>{c.created_by}</span>
                  <span className="act">
                    <button className="btn" onClick={() => openClaim(c.id)}>Inspect</button>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </>
  );
}

/** Audit read-only inspection: full summary + attributed audit trail. */
export function InspectView({ claim: c }: { claim: Claim }) {
  const { closeClaim } = useStore();
  const versions = persistence.versions(c.reference);

  return (
    <>
      <div>
        <button className="btn" onClick={closeClaim}>← Back to audit</button>
      </div>

      <div className="apphdr">
        <span className="brand" style={{ fontSize: 13 }}>Audit · Inspect</span>
        <span className="ref">{c.reference}</span>
        <StatusPill status={c.status} />
        <span className="sub">
          {c.patient.given} {c.patient.family} · NHI {c.patient.nhi || "—"} · created by {c.created_by}
        </span>
        <span className="grow" />
        <span className="sub">read-only</span>
      </div>

      <Summary claim={c} />

      <Card title="Audit trail · attributed change history">
        {versions.length === 0 ? (
          <p className="caption">No recorded changes for this claim.</p>
        ) : (
          <table className="tbl">
            <thead>
              <tr>
                <th>Ver</th>
                <th>When</th>
                <th>Author</th>
                <th>Role</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.version}>
                  <td>v{v.version}</td>
                  <td>{v.ts}</td>
                  <td>{v.author}</td>
                  <td><span className="pill">{v.role}</span></td>
                  <td>{v.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </>
  );
}
