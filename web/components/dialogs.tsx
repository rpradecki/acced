"use client";

import { useState } from "react";
import type { Claim } from "@/lib/types";
import { terminology } from "@/lib/connectors";
import { uid } from "@/lib/domain";
import { useStore } from "@/lib/store";
import { Banner, Field, Modal, Segmented } from "./ui";

const SIDES = ["Left", "Right", "Bilateral", "N/A"] as const;

export function AddDiagnosisDialog({ claim, onClose }: { claim: Claim; onClose: () => void }) {
  const { updateClaim } = useStore();
  const [scoped, setScoped] = useState(true);
  const [query, setQuery] = useState("");
  const [idx, setIdx] = useState(0);
  const [side, setSide] = useState<(typeof SIDES)[number]>("Left");

  const pool = terminology.search(query, scoped); // FHIR $expand (stub)
  const sel = pool[Math.min(idx, pool.length - 1)];

  return (
    <Modal
      title="Add diagnosis"
      onClose={onClose}
      footer={
        <>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button
            className="btn primary"
            disabled={!sel}
            onClick={() => {
              if (!sel) return;
              updateClaim(
                claim.id,
                (d) => {
                  d.diagnoses.push({
                    id: uid(), code: sel.code, display: sel.display, site: sel.site,
                    side, acc: sel.acc, primary: d.diagnoses.length === 0, status: "draft",
                  });
                },
                `diagnosis added (${sel.code})`,
              );
              onClose();
            }}
          >
            Add to claim
          </button>
        </>
      }
    >
      <label className="rowflex" style={{ fontSize: 12.5 }}>
        <input type="checkbox" checked={scoped} style={{ width: "auto" }} onChange={(e) => setScoped(e.target.checked)} />
        Scope to ACC-claimable concepts
      </label>

      <Field label="Search SNOMED CT">
        <input
          type="text"
          value={query}
          placeholder="e.g. sprain, wrist, laceration, knee"
          onChange={(e) => { setQuery(e.target.value); setIdx(0); }}
        />
      </Field>

      {pool.length === 0 ? (
        <Banner kind="info">No matches.</Banner>
      ) : (
        <>
          <Field label="Result">
            <select value={idx} onChange={(e) => setIdx(Number(e.target.value))}>
              {pool.map((t, i) => (
                <option key={t.code} value={i}>
                  {t.display} · {t.code} · {t.acc ? "ACC-eligible" : "NOT ACC-eligible"}
                </option>
              ))}
            </select>
          </Field>

          {sel &&
            (sel.acc ? (
              <Banner kind="ok">
                ✓ <b>{sel.display}</b> ({sel.code}) — member of the ACC claim reference set. Supports an ACC claim.
              </Banner>
            ) : (
              <Banner kind="err">
                ⚠ <b>{sel.display}</b> ({sel.code}) — <b>not</b> in the ACC claim reference set. Can be recorded, but
                cannot support an ACC claim on its own. Consider a specific injury + body site.
              </Banner>
            ))}

          <Field label="Body side">
            <Segmented options={SIDES} value={side} onChange={setSide} />
          </Field>
        </>
      )}
    </Modal>
  );
}

export function ChangeRequestDialog({ claim, onClose }: { claim: Claim; onClose: () => void }) {
  const { updateClaim } = useStore();
  const [query, setQuery] = useState("");
  const [idx, setIdx] = useState(0);
  const [side, setSide] = useState<(typeof SIDES)[number]>("Left");
  const [reason, setReason] = useState("");
  const [sameEvent, setSameEvent] = useState(false);
  const [bundle, setBundle] = useState(true);

  const pool = terminology.search(query, false);
  const sel = pool[Math.min(idx, pool.length - 1)];

  return (
    <Modal
      title="Add diagnosis to lodged ACC45"
      onClose={onClose}
      footer={
        <>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button
            className="btn primary"
            disabled={!sameEvent || !sel}
            onClick={() => {
              if (!sel) return;
              const reqId = uid();
              updateClaim(
                claim.id,
                (d) => {
                  d.change_requests.push({
                    id: reqId, kind: "add", code: sel.code, display: sel.display, side,
                    acc: sel.acc, same_event: sameEvent,
                    bundled: bundle ? "ACC18 medical certificate" : "—",
                    reason, status: "submitted",
                  });
                  d.diagnoses.push({
                    id: uid(), code: sel.code, display: sel.display, site: sel.site, side,
                    acc: sel.acc, primary: false, status: "change_pending", source_request: reqId,
                  });
                },
                `diagnosis change request (+${sel.code})`,
              );
              onClose();
            }}
          >
            Submit change request
          </button>
        </>
      }
    >
      <Banner kind="info">
        ℹ This creates a <b>Change-in-Diagnosis request</b> against the existing claim (not a re-lodgement). The new
        injury must be from the <b>same accident</b> already on this ACC45. It receives its own cover decision.
      </Banner>

      <Field label="Search SNOMED CT">
        <input type="text" value={query} placeholder="e.g. knee, sprain" onChange={(e) => { setQuery(e.target.value); setIdx(0); }} />
      </Field>

      {pool.length === 0 ? (
        <Banner kind="info">No matches.</Banner>
      ) : (
        <Field label="Result">
          <select value={idx} onChange={(e) => setIdx(Number(e.target.value))}>
            {pool.map((t, i) => (
              <option key={t.code} value={i}>
                {t.display} · {t.code} · {t.acc ? "ACC-eligible" : "NOT ACC-eligible"}
              </option>
            ))}
          </select>
        </Field>
      )}

      <Field label="Body side">
        <Segmented options={SIDES} value={side} onChange={setSide} />
      </Field>

      <Field label="Accident date (read-only)">
        <input type="text" value={claim.accident.adate ?? "—"} disabled readOnly />
      </Field>

      <Field label="Reason for adding">
        <textarea
          value={reason}
          placeholder="e.g. knee injured in the same fall, found on follow-up"
          onChange={(e) => setReason(e.target.value)}
        />
      </Field>

      <label className="rowflex" style={{ fontSize: 12.5 }}>
        <input type="checkbox" checked={sameEvent} style={{ width: "auto" }} onChange={(e) => setSameEvent(e.target.checked)} />
        This injury was caused by the accident already on this claim (same event)
      </label>
      <label className="rowflex" style={{ fontSize: 12.5 }}>
        <input type="checkbox" checked={bundle} style={{ width: "auto" }} onChange={(e) => setBundle(e.target.checked)} />
        Attach to the ACC18 medical certificate issued this encounter
      </label>

      {!sameEvent && (
        <Banner kind="warn">
          ⚠ If this injury is from a <b>different</b> accident, don&apos;t add it here — lodge a new ACC45 instead.
        </Banner>
      )}
    </Modal>
  );
}
