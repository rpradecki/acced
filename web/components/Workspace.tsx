"use client";

import { useStore, type Tab } from "@/lib/store";
import type { Claim } from "@/lib/types";
import { isExpired, validate } from "@/lib/domain";
import { auth } from "@/lib/connectors";
import { Banner, StatusPill, WindowPill } from "./ui";
import AdminPanel from "./AdminPanel";
import ClinicianPanel, { ClinicalReadOnly } from "./ClinicianPanel";
import ReviewPanel from "./ReviewPanel";

const TABS: [Tab, string][] = [
  ["admin", "📋  Administrative"],
  ["clin", "🩺  Clinician"],
  ["review", "✅  Review & lodge"],
];

export default function Workspace({ claim: c }: { claim: Claim }) {
  const { closeClaim, tab, setTab, role } = useStore();
  const { errors, canLodge } = validate(c);

  return (
    <>
      <div>
        <button className="btn" onClick={closeClaim}>← Home</button>
      </div>

      <div className="apphdr">
        <span className="brand" style={{ fontSize: 13 }}>Health NZ</span>
        <span className="ref">{c.reference}</span>
        <StatusPill status={c.status} />
        <WindowPill claim={c} />
        <span className="sub">
          {c.patient.given} {c.patient.family} · encounter {c.encounter.external_id} · accident{" "}
          {c.accident.adate ?? "—"}
        </span>
        <span className="grow" />
        <span className="sub">{canLodge ? "✓ ready" : `${errors.length} to fix`}</span>
      </div>

      {isExpired(c) && (
        <Banner kind="err">
          🔒 <b>Read-only — the 14-day update/revision/repair window has closed.</b> This referral can no longer be
          edited or lodged. (Ongoing certification would continue via a new ACC18.)
        </Banner>
      )}

      <div className="tabbar">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            className={`btn ${tab === key ? "primary" : ""}`}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "admin" && <AdminPanel claim={c} />}
      {tab === "clin" &&
        (auth.canEditClinical(role) ? <ClinicianPanel claim={c} /> : <ClinicalReadOnly claim={c} />)}
      {tab === "review" && <ReviewPanel claim={c} />}
    </>
  );
}
