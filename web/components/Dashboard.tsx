"use client";

import { useStore } from "@/lib/store";
import {
  PRACTICE_FACILITY, daysLeft, daysSinceAccident, isExpired, isSubmitted, readiness,
} from "@/lib/domain";
import type { Claim } from "@/lib/types";
import { auth } from "@/lib/connectors";
import { LodgementNote, ReadinessPill, StatusPill, WindowPill } from "./ui";

type RowKind = "unsubmitted" | "submitted" | "expired";

function SubmissionHeader({ kind }: { kind: RowKind }) {
  const last = kind === "unsubmitted" ? "Lodge by" : "Repair window";
  return (
    <div className="claimrow submissions head">
      <span>ACC45 no.</span>
      <span>Patient</span>
      <span>Status</span>
      <span>Accident</span>
      <span>{last}</span>
      <span />
    </div>
  );
}

function SubmissionRow({ claim, kind }: { claim: Claim; kind: RowKind }) {
  const { openClaim } = useStore();
  const readOnly = kind === "expired";
  return (
    <div className="claimrow submissions">
      <span className="ref">{claim.reference}</span>
      <span>
        {claim.patient.given} {claim.patient.family}
      </span>
      <span>
        {kind === "unsubmitted" ? (
          <ReadinessPill claim={claim} />
        ) : (
          <>
            <StatusPill status={claim.status} />
            {claim.decision && <span className="mono" style={{ marginLeft: 6 }}>{claim.decision}</span>}
          </>
        )}
      </span>
      <span>{claim.accident.adate ?? "—"}</span>
      <span>{kind === "unsubmitted" ? <LodgementNote claim={claim} /> : <WindowPill claim={claim} />}</span>
      <span className="act">
        <button
          className="btn"
          onClick={() => openClaim(claim.id, kind === "unsubmitted" ? "admin" : "review")}
        >
          {readOnly ? "View" : "Open"}
        </button>
      </span>
    </div>
  );
}

function PracticeRow({ claim }: { claim: Claim }) {
  const { openClaim } = useStore();
  const draftish = claim.status === "draft" || claim.status === "ready";
  return (
    <div className="claimrow practice">
      <span className="ref">{claim.reference}</span>
      <span>
        {claim.patient.given} {claim.patient.family}
      </span>
      <span>
        {draftish ? (
          <ReadinessPill claim={claim} />
        ) : (
          <>
            <StatusPill status={claim.status} />
            {claim.decision && <span className="mono" style={{ marginLeft: 6 }}>{claim.decision}</span>}
          </>
        )}
      </span>
      <span>{claim.accident.adate ?? "—"}</span>
      <span className="mono">{claim.created_by}</span>
      <span className="act">
        <button className="btn" onClick={() => openClaim(claim.id, draftish ? "admin" : "review")}>
          Open
        </button>
      </span>
    </div>
  );
}

export default function Dashboard() {
  const { claims, touched, role, createClaim } = useStore();
  const user = auth.currentUser(role);

  // Single-practice prototype: every claim belongs to this one facility, so there is no
  // facility filter. Claims split into a per-identity working set (created or opened by
  // you) and the rest of the practice's pool. Multi-facility scoping via RLS, and
  // optimistic locking for concurrent edits, are production concerns.
  const working = claims.filter((c) => touched.has(c.reference));
  const pool = claims.filter((c) => !touched.has(c.reference));

  const unsubmitted = working
    .filter((c) => c.status === "draft" || c.status === "ready")
    .sort((a, b) => (daysSinceAccident(b) ?? -1) - (daysSinceAccident(a) ?? -1));
  const submitted = working
    .filter((c) => isSubmitted(c) && !isExpired(c))
    .sort((a, b) => (daysLeft(a) ?? 0) - (daysLeft(b) ?? 0));
  const expired = working.filter(isExpired);

  const readyToLodge = unsubmitted.filter((c) => readiness(c).code === "ready").length;
  const repair = submitted.filter((c) => c.status === "held" || c.status === "declined").length;
  const expiring = submitted.filter((c) => {
    const d = daysLeft(c);
    return d !== null && d > 0 && d <= 3;
  }).length;

  const metrics: [number, string, string][] = [
    [unsubmitted.length, "Unsubmitted", ""],
    [readyToLodge, "Ready to lodge", ""],
    [submitted.length, "Submitted (14-day)", ""],
    [repair, "Needs repair", repair ? "err" : ""],
    [expiring, "Expiring ≤3 days", expiring ? "warn" : ""],
  ];

  return (
    <>
      <div className="apphdr">
        <span className="brand">
          Health New Zealand <span style={{ fontWeight: 400, opacity: 0.75 }}>| Te Whatu Ora</span>
        </span>
        <span className="sub">ACC Claim Console · research mockup</span>
        <span className="grow" />
        <span className="sub">
          {user.name} · {user.role_label}
        </span>
      </div>

      <div className="pagehdr">
        <div>
          <h4>ACC submissions</h4>
          <p className="lede">
            Unsubmitted referrals have no edit clock — but ACC should be lodged <b>within 12 months</b> of the
            accident (later needs supporting records). Once <b>submitted</b>, a referral stays editable for{" "}
            <b>14 days</b> for update, revision or repair, then drops off (read-only).
          </p>
        </div>
        <span className="grow" />
        <button className="btn primary" onClick={createClaim}>
          ＋ New ACC45 claim
        </button>
      </div>

      <div className="metricrow">
        {metrics.map(([v, label, cls]) => (
          <div className={`metric ${cls}`} key={label}>
            <span className="mv">{v}</span>
            <span className="ml">{label}</span>
          </div>
        ))}
      </div>

      <Panelish title="My Worklist" empty={!unsubmitted.length} emptyText="Nothing unsubmitted.">
        <SubmissionHeader kind="unsubmitted" />
        {unsubmitted.map((c) => (
          <SubmissionRow key={c.id} claim={c} kind="unsubmitted" />
        ))}
      </Panelish>

      <Panelish
        title="My Modifiable Submissions"
        empty={!submitted.length}
        emptyText="Nothing submitted in the last 14 days."
      >
        <SubmissionHeader kind="submitted" />
        {submitted.map((c) => (
          <SubmissionRow key={c.id} claim={c} kind="submitted" />
        ))}
      </Panelish>

      <details className="exp" open>
        <summary>{PRACTICE_FACILITY} Global List</summary>
        <div className="panel-body">
          {pool.length === 0 ? (
            <p className="caption">You&apos;ve opened every claim in the practice.</p>
          ) : (
            <div>
              <div className="claimrow practice head">
                <span>ACC45 no.</span>
                <span>Patient</span>
                <span>Status</span>
                <span>Accident</span>
                <span>Created by</span>
                <span />
              </div>
              {[...pool]
                .sort((a, b) => a.reference.localeCompare(b.reference))
                .map((c) => (
                  <PracticeRow key={c.id} claim={c} />
                ))}
            </div>
          )}
        </div>
      </details>

      {expired.length > 0 && (
        <details className="exp">
          <summary>Past Submissions · {expired.length}</summary>
          <div className="panel-body">
            <p className="caption">
              The 14-day post-lodgement update/revision/repair window has closed. Shown for reference only.
            </p>
            <div>
              <SubmissionHeader kind="submitted" />
              {expired.map((c) => (
                <SubmissionRow key={c.id} claim={c} kind="expired" />
              ))}
            </div>
          </div>
        </details>
      )}
    </>
  );
}

/** Panel that shows an empty caption instead of its rows when there's nothing to list. */
function Panelish({
  title, children, empty, emptyText,
}: {
  title: string;
  children: React.ReactNode;
  empty: boolean;
  emptyText: string;
}) {
  return (
    <section className="panel">
      <div className="panelhdr">{title}</div>
      <div className="panel-body">
        {empty ? <p className="caption">{emptyText}</p> : <div>{children}</div>}
      </div>
    </section>
  );
}
