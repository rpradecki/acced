"use client";

import { useStore } from "@/lib/store";
import type { Claim, YesNo } from "@/lib/types";
import { EMP_STATUSES, SCENES, SPORTS } from "@/lib/domain";
import { nhi } from "@/lib/connectors";
import { Card, Field, Segmented } from "./ui";

const YN: readonly YesNo[] = ["No", "Yes"] as const;

export default function AdminPanel({ claim }: { claim: Claim }) {
  const { updateClaim } = useStore();
  const c = claim;
  const set = (mutate: (d: Claim) => void, action?: string) => updateClaim(c.id, mutate, action);

  const e = c.encounter;
  const p = c.patient;
  const em = c.employment;
  const a = c.accident;

  return (
    <>
      <Card title="Encounter context · from PAS/PMS">
        <div className="chips">
          <span className="kv">Encounter <b>{e.external_id}</b></span>
          <span className="kv">Source <b>{e.source_system}</b></span>
          <span className="kv">Facility <b>{e.facility}</b></span>
          <span className="kv">Provider <b>{e.provider}</b></span>
          <span className="kv">
            ACC45 no. <b>{c.reference}</b> ·{" "}
            {c.number_source === "acc_allocation_api" ? "ACC allocation API" : "pre-allocated block"}
          </span>
        </div>
        <div className="mono">Identity inherited from the PMS — verify, don&apos;t re-key.</div>
      </Card>

      <div className="grid2">
        <Card title="Patient · ACC45 Part A">
          <Field label="Given name *">
            <input type="text" value={p.given} onChange={(ev) => set((d) => { d.patient.given = ev.target.value; })} />
          </Field>
          <Field label="Family name *">
            <input type="text" value={p.family} onChange={(ev) => set((d) => { d.patient.family = ev.target.value; })} />
          </Field>
          <div className="grid2">
            <Field label="DOB * (YYYY-MM-DD)">
              <input type="text" value={p.dob} onChange={(ev) => set((d) => { d.patient.dob = ev.target.value; })} />
            </Field>
            <Field label="NHI">
              <input
                type="text"
                value={p.nhi}
                onChange={(ev) => set((d) => { d.patient.nhi = ev.target.value.toUpperCase(); })}
              />
            </Field>
          </div>
          {p.nhi &&
            (nhi.validate(p.nhi) ? (
              <div className="rowflex">
                <span className="pill ok">NHI format valid</span>
                <span className="mono">check-digit &amp; demographics via NHI service (stub)</span>
              </div>
            ) : (
              <span className="pill err">NHI format invalid</span>
            ))}
          <div className="grid2">
            <Field label="Mobile">
              <input type="text" value={p.mobile} onChange={(ev) => set((d) => { d.patient.mobile = ev.target.value; })} />
            </Field>
            <Field label="Email">
              <input type="text" value={p.email} onChange={(ev) => set((d) => { d.patient.email = ev.target.value; })} />
            </Field>
          </div>
          <Field label="Address">
            <input type="text" value={p.address} onChange={(ev) => set((d) => { d.patient.address = ev.target.value; })} />
          </Field>
        </Card>

        <div className="stack">
          <Card title="Employment · ACC45 Part B">
            <Field label="Employment status">
              <select value={em.status} onChange={(ev) => set((d) => { d.employment.status = ev.target.value; })}>
                {EMP_STATUSES.map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </Field>
            <Field label="Occupation">
              <input
                type="text"
                value={em.occupation}
                disabled={em.status === "Not employed in NZ"}
                onChange={(ev) => set((d) => { d.employment.occupation = ev.target.value; })}
              />
            </Field>
            <Field label="Employer">
              <input
                type="text"
                value={em.employer}
                disabled={em.status !== "Employee"}
                placeholder={em.status === "Employee" ? "Required for employees" : "n/a"}
                onChange={(ev) => set((d) => { d.employment.employer = ev.target.value; })}
              />
            </Field>
          </Card>

          <Card title="Patient consent · ACC45 Part E">
            {c.consent.given ? (
              <div className="bnr ok" style={{ margin: "2px 0" }}>
                ✓ <b>Consent given</b> — {c.consent.at}. All three authorisations captured.
              </div>
            ) : (
              <>
                <p className="caption">
                  3-question script: (1) collect/use/disclose, (2) true &amp; correct, (3) authorise lodgement.
                </p>
                <button
                  className="btn primary"
                  onClick={() =>
                    set((d) => {
                      d.consent = {
                        given: true,
                        at: new Date().toLocaleString("en-NZ", {
                          day: "2-digit", month: "2-digit", year: "numeric",
                          hour: "2-digit", minute: "2-digit", hour12: false,
                        }),
                      };
                    }, "consent recorded")
                  }
                >
                  Record patient consent (all three = Yes)
                </button>
              </>
            )}
          </Card>
        </div>
      </div>

      <Card title="Accident · ACC45 Part B">
        <div className="grid3">
          <Field label="Date of accident *">
            <input
              type="date"
              value={a.adate ?? ""}
              onChange={(ev) => set((d) => { d.accident.adate = ev.target.value || null; })}
            />
          </Field>
          <Field label="Time">
            <input type="text" value={a.atime} onChange={(ev) => set((d) => { d.accident.atime = ev.target.value; })} />
          </Field>
          <Field label="Location">
            <input type="text" value={a.location} onChange={(ev) => set((d) => { d.accident.location = ev.target.value; })} />
          </Field>
        </div>

        <div className="grid4">
          <Field label="Scene">
            <select value={a.scene} onChange={(ev) => set((d) => { d.accident.scene = ev.target.value; })}>
              {SCENES.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </Field>
          <Field label="Workplace?">
            <Segmented options={YN} value={a.workplace} onChange={(v) => set((d) => { d.accident.workplace = v; })} />
          </Field>
          <Field label="Vehicle on road?">
            <Segmented options={YN} value={a.vehicle} onChange={(v) => set((d) => { d.accident.vehicle = v; })} />
          </Field>
          <Field label="Sporting?">
            <Segmented
              options={YN}
              value={a.sporting}
              onChange={(v) =>
                set((d) => {
                  d.accident.sporting = v;
                  if (v === "No") d.accident.sport = "";
                })
              }
            />
          </Field>
        </div>

        {/* Sport dropdown appears only when "Sporting injury?" is Yes (mirrors the ACC45). */}
        {a.sporting === "Yes" && (
          <Field label="Sport *">
            <select value={a.sport} onChange={(ev) => set((d) => { d.accident.sport = ev.target.value; })}>
              <option value="">— select sport —</option>
              {SPORTS.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </Field>
        )}

        <Field label="Cause of injury (mechanism) *">
          <textarea
            value={a.cause}
            placeholder="e.g. walking to the kitchen – tripped over own feet – fell to ground"
            onChange={(ev) => set((d) => { d.accident.cause = ev.target.value; })}
          />
        </Field>
      </Card>
    </>
  );
}
