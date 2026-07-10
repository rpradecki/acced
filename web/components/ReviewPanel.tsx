"use client";

import { useState } from "react";
import { useStore } from "@/lib/store";
import type { Claim, ClaimStatus } from "@/lib/types";
import { STATUS_LABEL, isExpired, todayISO, validate } from "@/lib/domain";
import { acc, auth, notification } from "@/lib/connectors";
import { Banner, Card, DefList, DxTable, WideRow } from "./ui";
import { ChangeRequestDialog } from "./dialogs";

/** Full ACC45 summary of everything entered on the form. */
export function Summary({ claim: c }: { claim: Claim }) {
  const { patient: p, employment: e, accident: a, capacity: cap, declaration: dec, flags: fl } = c;
  const restr = cap.restrictions || cap.justification;

  return (
    <Card>
      <div className="sec">Claim summary · ACC45</div>
      <DefList
        pairs={[
          ["ACC45 number", c.reference],
          ["Status", STATUS_LABEL[c.status].label],
          ["Encounter", c.encounter.external_id],
          ["Source system", c.encounter.source_system],
          ["Facility", c.encounter.facility],
          ["Attending provider", c.encounter.provider],
        ]}
      />

      <div className="sec">Patient · Part A</div>
      <DefList
        pairs={[
          ["Name", `${p.given} ${p.family}`.trim()],
          ["Date of birth", p.dob],
          ["NHI", p.nhi],
          ["Mobile", p.mobile],
          ["Email", p.email],
          ["Address", p.address],
        ]}
      />

      <div className="sec">Employment · Part B</div>
      <DefList pairs={[["Employment status", e.status], ["Occupation", e.occupation], ["Employer", e.employer]]} />

      <div className="sec">Accident · Part B</div>
      <DefList
        pairs={[
          ["Date / time", `${a.adate ?? "—"} ${a.atime}`.trim()],
          ["Location", a.location],
          ["Scene", a.scene],
          ["Workplace accident", a.workplace],
          ["Moving vehicle on road", a.vehicle],
          ["Sporting injury", a.sporting + (a.sporting === "Yes" && a.sport ? ` — ${a.sport}` : "")],
        ]}
      />
      <WideRow label="Cause of injury" value={a.cause} />

      <div className="sec">Consent · Part E (patient)</div>
      {c.consent.given ? (
        <div className="rowflex">
          <span className="pill ok">Consent recorded</span>
          <span className="kv">Given {c.consent.at} · all three authorisations</span>
        </div>
      ) : (
        <span className="pill err">Consent not recorded</span>
      )}

      <div className="sec">Diagnoses · Part C</div>
      {c.diagnoses.length ? <DxTable diagnoses={c.diagnoses} /> : <span className="pill err">No diagnoses entered</span>}
      <div className="chips">
        <span className="kv">Gradual process <b>{fl.gradual}</b></span>
        <span className="kv">Treatment injury <b>{fl.treatment}</b></span>
        <span className="kv">Admitted <b>{fl.admitted}</b></span>
        <span className="kv">Home assistance <b>{fl.home}</b></span>
      </div>

      <div className="sec">Ability to work · Part D / ACC18</div>
      <DefList
        pairs={[
          ["Normal work exertion", cap.exertion],
          ["Work capacity", cap.state],
          ["Certificate", cap.cert_type],
          ["Valid", `${cap.valid_from ?? "—"} → ${cap.valid_to ?? "—"}`],
        ]}
      />
      {restr && <WideRow label="Restrictions / justification" value={restr} />}

      <div className="sec">Practitioner declaration · Part E</div>
      {dec.made ? (
        <div className="rowflex">
          <span className="pill ok">Declaration made</span>
          <span className="kv">{dec.date} · {dec.by} · provider {dec.provider_no}</span>
        </div>
      ) : (
        <span className="pill err">Declaration not completed</span>
      )}
    </Card>
  );
}

export default function ReviewPanel({ claim: c }: { claim: Claim }) {
  const { role, updateClaim } = useStore();
  const [dialog, setDialog] = useState(false);
  const { errors, warnings, canLodge } = validate(c);
  const expired = isExpired(c);
  const unsubmitted = c.status === "draft" || c.status === "ready";

  const decide = (choice: "Accepted" | "Held" | "Declined") =>
    updateClaim(
      c.id,
      (d) => {
        d.status = choice.toLowerCase() as ClaimStatus;
        d.decision = acc.decision(choice);
      },
      `ACC decision: ${choice}`,
    );

  return (
    <>
      {dialog && <ChangeRequestDialog claim={c} onClose={() => setDialog(false)} />}

      <Card title="Lodgement readiness">
        {errors.length === 0 ? (
          <Banner kind="ok">✓ All mandatory requirements met — ready to lodge.</Banner>
        ) : (
          <Banner kind="err">
            <b>Cannot lodge yet:</b>
            <ul>
              {errors.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          </Banner>
        )}
        {warnings.length > 0 && (
          <Banner kind="warn">
            <b>Warnings (non-blocking):</b>
            <ul>
              {warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </Banner>
        )}

        {unsubmitted && !auth.canSubmit(role) ? (
          <Banner kind="warn">
            🔒 Your <b>clerical</b> role can prepare and review this claim but cannot submit it. A clinician lodges
            the ACC45.
          </Banner>
        ) : (
          unsubmitted && (
            <div className="rowflex">
              <button
                className="btn primary"
                disabled={!canLodge || expired}
                onClick={() => {
                  updateClaim(
                    c.id,
                    (d) => {
                      d.diagnoses.forEach((x) => { x.status = "lodged"; });
                      d.status = "lodged";
                      d.lodged_on = todayISO(); // starts the 14-day repair window
                      d.decision = acc.lodge(d);
                    },
                    "lodged ACC45",
                  );
                  notification.sendDecisionSms(c.patient.mobile, c.reference, "Received");
                }}
              >
                Complete &amp; lodge ACC45
              </button>
              <span className="caption">
                {expired
                  ? "Edit window expired — cannot lodge."
                  : canLodge
                    ? "Validation passed."
                    : "Complete is disabled until validation passes."}
              </span>
            </div>
          )
        )}
      </Card>

      <Summary claim={c} />

      {!unsubmitted && (
        <Card>
          <Banner kind="info">
            ✓ ACC45 lodged. Decision: <b>{c.decision}</b>. Diagnosis grid is now read-only; further clinical changes go
            through a diagnosis-change request.
          </Banner>

          {c.status === "lodged" && (
            <>
              <p className="caption">Simulate ACC decision:</p>
              <div className="rowflex">
                <button className="btn" onClick={() => decide("Accepted")}>Accepted</button>
                <button className="btn" onClick={() => decide("Held")}>Held</button>
                <button className="btn" onClick={() => decide("Declined")}>Declined</button>
              </div>
            </>
          )}

          <div className="sec">Post-lodgement diagnosis changes</div>
          {auth.canEditClinical(role) ? (
            <div>
              <button className="btn primary" onClick={() => setDialog(true)}>
                ＋ Add / change diagnosis (post-lodgement)
              </button>
            </div>
          ) : (
            <p className="caption">Post-lodgement diagnosis changes are a clinical action (clinician role).</p>
          )}

          {c.change_requests.length > 0 && (
            <table className="tbl">
              <thead>
                <tr>
                  <th>Kind</th>
                  <th>Diagnosis</th>
                  <th>Same event</th>
                  <th>Bundled</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {c.change_requests.map((r) => (
                  <tr key={r.id}>
                    <td>{r.kind}</td>
                    <td>
                      {r.display} <span className="mono">{r.code}</span>
                    </td>
                    <td>{r.same_event ? "✓" : "—"}</td>
                    <td>{r.bundled}</td>
                    <td>
                      <span className="pill warn">{r.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}
    </>
  );
}
