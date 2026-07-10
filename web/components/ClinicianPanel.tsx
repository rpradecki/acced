"use client";

import { useState } from "react";
import { useStore } from "@/lib/store";
import type { Capacity, Claim, YesNo } from "@/lib/types";
import { CAPACITY_STATES, CERT_TYPES, EXERTION, eligibleDx, isExpired, todayISO } from "@/lib/domain";
import { auth, hpi } from "@/lib/connectors";
import { Banner, Card, DxTable, Field, Segmented } from "./ui";
import { AddDiagnosisDialog } from "./dialogs";

const YN: readonly YesNo[] = ["No", "Yes"] as const;

export default function ClinicianPanel({ claim }: { claim: Claim }) {
  const { updateClaim, role } = useStore();
  const [dialog, setDialog] = useState(false);
  const c = claim;
  const set = (mutate: (d: Claim) => void, action?: string) => updateClaim(c.id, mutate, action);

  const isPrescriber = auth.canSignPartE(role);
  const locked = !["draft", "ready"].includes(c.status) || isExpired(c);
  const eligible = eligibleDx(c);
  const cap = c.capacity;
  const dec = c.declaration;
  const f = c.flags;

  return (
    <>
      {dialog && <AddDiagnosisDialog claim={c} onClose={() => setDialog(false)} />}

      <Card title="Context · from admin / encounter">
        <div className="chips">
          <span className="kv">
            Patient <b>{c.patient.given} {c.patient.family}</b> ({c.patient.dob})
          </span>
          <span className="kv">Accident <b>{c.accident.adate ?? "— not set"}</b></span>
          <span className="kv">Scene <b>{c.accident.scene}</b></span>
          <span className="kv">
            Consent {c.consent.given ? <span className="pill ok">recorded</span> : <span className="pill err">missing</span>}
          </span>
        </div>
        {c.accident.cause && <div className="mono">Cause: {c.accident.cause}</div>}
      </Card>

      <Card>
        <div className="rowflex">
          <div className="sec" style={{ margin: 0 }}>Injury diagnosis &amp; assistance · ACC45 Part C</div>
          <span className="grow" style={{ flex: 1 }} />
          <span className="pill blue">
            {c.diagnoses.length} dx · {eligible.length} ACC-eligible
          </span>
        </div>

        {!locked ? (
          <div>
            <button className="btn" onClick={() => setDialog(true)}>＋ Add diagnosis</button>
          </div>
        ) : (
          <span className="pill warn">Lodged — grid read-only; use Review tab to add a change</span>
        )}

        {c.diagnoses.length > 0 ? (
          <>
            <DxTable diagnoses={c.diagnoses} />
            {!locked && (
              <details className="exp">
                <summary>Edit diagnoses (remove)</summary>
                <div className="panel-body">
                  {c.diagnoses.map((d) => (
                    <div className="rowflex" key={d.id}>
                      <span style={{ flex: 1 }}>
                        {d.display} <span className="mono">{d.code}</span>
                      </span>
                      <button
                        className="btn"
                        onClick={() =>
                          set((x) => { x.diagnoses = x.diagnoses.filter((y) => y.id !== d.id); },
                            `diagnosis removed (${d.code})`)
                        }
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </>
        ) : (
          <Banner kind="err">✱ At least one injury diagnosis is needed.</Banner>
        )}

        {c.diagnoses.length > 0 && eligible.length === 0 && (
          <Banner kind="err">
            ⚠ <b>No ACC-eligible diagnosis yet.</b> Every diagnosis on this claim is outside the ACC claim reference
            set. Add at least one ACC-eligible injury to lodge — this claim cannot be submitted as-is.
          </Banner>
        )}
      </Card>

      <div className="grid2">
        <Card title="Clinical flags">
          <Field label="Work-related gradual process?">
            <Segmented options={YN} value={f.gradual} onChange={(v) => set((d) => { d.flags.gradual = v; })} />
          </Field>
          <Field label="Treatment injury?">
            <Segmented options={YN} value={f.treatment} onChange={(v) => set((d) => { d.flags.treatment = v; })} />
          </Field>
          <Field label="Home assistance required?">
            <Segmented options={YN} value={f.home} onChange={(v) => set((d) => { d.flags.home = v; })} />
          </Field>
          <Field label="Patient admitted?">
            <Segmented options={YN} value={f.admitted} onChange={(v) => set((d) => { d.flags.admitted = v; })} />
          </Field>
          {f.treatment === "Yes" && (
            <Banner kind="warn">ℹ Treatment injury — ACC2152 + patient notes required before lodgement.</Banner>
          )}
          {f.gradual === "Yes" && (
            <Banner kind="warn">ℹ Gradual process — medical practitioner only; work history needed.</Banner>
          )}
        </Card>

        <Card title="Ability to work · Part D / ACC18">
          <Field label="Normal work exertion">
            <select value={cap.exertion} onChange={(e) => set((d) => { d.capacity.exertion = e.target.value; })}>
              {EXERTION.map((x) => (
                <option key={x || "none"} value={x}>{x || "—"}</option>
              ))}
            </select>
          </Field>
          <Field label="Work capacity">
            <Segmented
              options={CAPACITY_STATES}
              value={cap.state}
              onChange={(v) => set((d) => { d.capacity.state = v as Capacity; })}
            />
          </Field>
          {cap.state === "Fit for selected work" && (
            <Field label="Restrictions / activities & type of work *">
              <textarea
                value={cap.restrictions}
                placeholder="e.g. seated duties, no lifting >5kg, max 4 hrs/day"
                onChange={(e) => set((d) => { d.capacity.restrictions = e.target.value; })}
              />
            </Field>
          )}
          {cap.state === "Fully unfit" && (
            <Field label="Justification (return would risk health/safety) *">
              <textarea
                value={cap.justification}
                onChange={(e) => set((d) => { d.capacity.justification = e.target.value; })}
              />
            </Field>
          )}
          <div className="grid2">
            <Field label="Certificate">
              <select value={cap.cert_type} onChange={(e) => set((d) => { d.capacity.cert_type = e.target.value; })}>
                {CERT_TYPES.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </Field>
            <div className="stack">
              <Field label="Valid from">
                <input
                  type="date"
                  value={cap.valid_from ?? ""}
                  onChange={(e) => set((d) => { d.capacity.valid_from = e.target.value || null; })}
                />
              </Field>
              <Field label="Valid to">
                <input
                  type="date"
                  value={cap.valid_to ?? ""}
                  onChange={(e) => set((d) => { d.capacity.valid_to = e.target.value || null; })}
                />
              </Field>
            </div>
          </div>
          {(cap.state === "Fit for selected work" || cap.state === "Fully unfit") && (
            <p className="caption">With prior earnings, may enable weekly compensation (informational).</p>
          )}
        </Card>
      </div>

      <Card title="Practitioner declaration · ACC45 Part E">
        {!isPrescriber && (
          <Banner kind="warn">
            🔒 <b>Part E is restricted to doctors and nurse practitioners.</b> Switch to the clinical role in the
            sidebar to sign, or route to an eligible colleague.
          </Banner>
        )}
        <p className="caption">
          I certify I have personally examined the patient, the condition results from an accident, and the patient
          authorised me to lodge this claim.
        </p>
        <div className="grid2">
          <Field label="Provider number">
            <input
              type="text"
              value={dec.provider_no}
              placeholder="e.g. HP-44921"
              disabled={!isPrescriber}
              onChange={(e) => set((d) => { d.declaration.provider_no = e.target.value; })}
            />
          </Field>
          <div style={{ alignSelf: "flex-end" }}>
            {dec.made ? (
              <div className="bnr ok" style={{ margin: 0 }}>
                ✓ Declaration made {dec.date} by {dec.by}.
              </div>
            ) : (
              <button
                className="btn primary"
                disabled={!isPrescriber}
                onClick={() =>
                  set((d) => {
                    d.declaration.made = true;
                    d.declaration.date = todayISO();
                    d.declaration.by = auth.currentUser(role).name;
                    if (!d.declaration.provider_no) d.declaration.provider_no = hpi.defaultProviderNumber();
                  }, "Part E declaration signed")
                }
              >
                Complete declaration (Today)
              </button>
            )}
          </div>
        </div>
      </Card>
    </>
  );
}

/** Clinician tab rendered read-only for the clerical role (view, not edit). */
export function ClinicalReadOnly({ claim: c }: { claim: Claim }) {
  const { flags: fl, capacity: cap, declaration: dec } = c;
  const restr = cap.restrictions || cap.justification;
  return (
    <>
      <Banner kind="info">
        👁 <b>Clinical section — read-only.</b> Your clerical role can view but not edit the clinical assessment; a
        clinician completes and signs it.
      </Banner>
      <Card title="Injury diagnosis & assistance · Part C">
        {c.diagnoses.length ? <DxTable diagnoses={c.diagnoses} /> : <span className="pill err">No diagnoses entered</span>}
        <div className="chips">
          <span className="kv">Gradual process <b>{fl.gradual}</b></span>
          <span className="kv">Treatment injury <b>{fl.treatment}</b></span>
          <span className="kv">Admitted <b>{fl.admitted}</b></span>
          <span className="kv">Home assistance <b>{fl.home}</b></span>
        </div>
      </Card>
      <Card title="Ability to work · Part D / ACC18">
        <div className="chips">
          <span className="kv">Exertion <b>{cap.exertion || "—"}</b></span>
          <span className="kv">Capacity <b>{cap.state || "—"}</b></span>
          <span className="kv">Certificate <b>{cap.cert_type}</b></span>
          <span className="kv">Valid <b>{cap.valid_from ?? "—"} → {cap.valid_to ?? "—"}</b></span>
        </div>
        {restr && <div className="kv" style={{ display: "block", marginTop: 4 }}>{restr}</div>}
      </Card>
      <Card title="Practitioner declaration · Part E">
        {dec.made ? (
          <div className="rowflex">
            <span className="pill ok">Declaration made</span>
            <span className="kv">{dec.date} · {dec.by}</span>
          </div>
        ) : (
          <span className="pill err">Declaration not completed</span>
        )}
      </Card>
    </>
  );
}
