// Sample pre-saved claims — openable & editable from the dashboard.
// created_by is distributed across the simulated identities so each user starts with a
// sensible working set and sees colleagues' untouched claims in the practice pool.

import type { Claim, Diagnosis, ClaimStatus } from "./types";
import { addDaysISO, todayISO, uid } from "./domain";
import { acc, persistence, pms } from "./connectors";

function base(reference: string): Claim {
  return {
    id: uid(),
    reference,
    number_source: "acc_allocation_api",
    status: "draft",
    decision: null,
    acknowledged_at: null,
    created: todayISO(),
    created_by: "Dr A. Rangi",
    lodged_on: null,
    encounter: {
      external_id: "ENC-" + Math.floor(100000 + Math.random() * 900000),
      source: "pms_context",
      facility: "Riverside Medical Centre",
      provider: "Dr A. Rangi (GP)",
      klass: "Outpatient / GP consult",
      source_system: "Medtech PMS",
    },
    patient: { pas_id: "", given: "", family: "", dob: "", nhi: "", mobile: "", email: "", address: "" },
    employment: { status: "Not employed in NZ", occupation: "Unemployed", employer: "" },
    accident: {
      adate: null, atime: "", location: "", scene: "Home",
      workplace: "No", vehicle: "No", sporting: "No", sport: "", cause: "",
    },
    consent: { given: false, at: null },
    diagnoses: [],
    flags: { gradual: "No", treatment: "No", admitted: "No", home: "No" },
    capacity: {
      exertion: "", state: "", restrictions: "", justification: "",
      cert_type: "ACC45 initial (≤14 days)", valid_from: null, valid_to: null,
    },
    declaration: { made: false, date: null, by: null, provider_no: "" },
    change_requests: [],
  };
}

function dx(
  code: string, display: string, side: string, accEligible: boolean,
  status = "draft", primary = false,
): Diagnosis {
  return { id: uid(), code, display, site: "", side, acc: accEligible, primary, status };
}

export function newClaim(seq: number, createdBy: string): Claim {
  const ctx = pms.getEncounterContext();
  const c = base(acc.allocateClaimNumber(seq));
  c.created_by = createdBy;
  c.encounter = ctx.encounter;
  c.patient = ctx.patient;
  c.accident = { ...c.accident, atime: "08:34", location: "Christchurch City" };
  return c;
}

export function seedClaims(): Claim[] {
  const today = todayISO();

  // 0) Early-stage DRAFT — patient from PMS but accident/consent not done → "Admin step needed".
  const c0 = base("IO16453");
  Object.assign(c0, { status: "draft" as ClaimStatus, created: today, created_by: "R. Patel" });
  c0.patient = { pas_id: "PAS-90011", given: "Hemi", family: "Walker", dob: "2001-05-08", nhi: "RTK1180", mobile: "021 004 5567", email: "", address: "12 Kauri Ave, Christchurch 8013" };
  c0.accident = { ...c0.accident, location: "Christchurch City" };

  // 1) In-progress DRAFT — consent + one diagnosis, not yet certified/declared.
  const c1 = base("IO16452");
  Object.assign(c1, { status: "draft" as ClaimStatus, created: addDaysISO(today, -3), created_by: "R. Patel" });
  c1.patient = { pas_id: "PAS-40021", given: "Aroha", family: "Ngata", dob: "1991-06-02", nhi: "KLP2286", mobile: "021 448 1190", email: "", address: "9 Tui Lane, Christchurch 8014" };
  c1.employment = { status: "Employee", occupation: "Warehouse assistant", employer: "Southern Distribution Ltd" };
  c1.accident = { adate: "2026-07-06", atime: "14:20", location: "Christchurch City", scene: "Work", workplace: "Yes", vehicle: "No", sporting: "No", sport: "", cause: "lifting a box off a pallet – felt sudden shoulder pain" };
  c1.consent = { given: true, at: "06/07/2026 14:40" };
  c1.diagnoses = [dx("209815008", "Sprain of rotator cuff (shoulder)", "Right", true, "draft", true)];

  // 2) READY to lodge — fully valid.
  const c2 = base("IO16454");
  Object.assign(c2, { status: "ready" as ClaimStatus, created: addDaysISO(today, -1) });
  c2.patient = { pas_id: "PAS-77310", given: "David", family: "Thorne", dob: "1974-11-19", nhi: "MTR9043", mobile: "027 220 6655", email: "", address: "22 Kowhai Road, Rangiora 7400" };
  c2.employment = { status: "Self-employed", occupation: "Builder", employer: "" };
  c2.accident = { adate: "2026-07-07", atime: "09:05", location: "Rangiora", scene: "Home", workplace: "No", vehicle: "No", sporting: "No", sport: "", cause: "slipped off a step ladder – landed awkwardly on left ankle" };
  c2.consent = { given: true, at: "07/07/2026 09:30" };
  c2.diagnoses = [dx("283384001", "Sprain of ligament of ankle", "Left", true, "draft", true)];
  c2.capacity = { exertion: "Heavy", state: "Fit for selected work", restrictions: "seated/office duties only, no ladder work, no lifting >5kg, max 6 hrs/day", justification: "", cert_type: "ACC18 (beyond 14 days)", valid_from: "2026-07-07", valid_to: "2026-07-21" };
  c2.declaration = { made: true, date: "2026-07-07", by: "Dr A. Rangi", provider_no: "HP-44921" };

  // 3) LODGED / ACCEPTED — grid read-only; edit via post-lodgement change request.
  const c3 = base("IO16456");
  Object.assign(c3, { status: "accepted" as ClaimStatus, decision: "Accepted", created: addDaysISO(today, -9), lodged_on: addDaysISO(today, -9), acknowledged_at: `${addDaysISO(today, -9)} 09:00:00` });
  c3.patient = { pas_id: "PAS-51188", given: "Sina", family: "Faleolo", dob: "1998-02-27", nhi: "NBW7712", mobile: "022 909 3312", email: "", address: "5 Harakeke Street, Christchurch 8025" };
  c3.employment = { status: "Employee", occupation: "Chef", employer: "Harbourview Restaurant" };
  c3.accident = { adate: "2026-06-30", atime: "19:45", location: "Christchurch City", scene: "Work", workplace: "Yes", vehicle: "No", sporting: "No", sport: "", cause: "slipped on wet kitchen floor – put out right hand to break the fall" };
  c3.consent = { given: true, at: "30/06/2026 20:10" };
  c3.diagnoses = [dx("20946005", "Fracture of distal radius (wrist)", "Right", true, "accepted", true)];
  c3.capacity = { exertion: "Medium", state: "Fully unfit", restrictions: "", justification: "wrist immobilised in cast; unable to perform any kitchen duties safely", cert_type: "ACC18 (beyond 14 days)", valid_from: "2026-06-30", valid_to: "2026-07-28" };
  c3.declaration = { made: true, date: "2026-06-30", by: "Dr A. Rangi", provider_no: "HP-44921" };

  // 4) DECLINED — needs repair, edit window closing.
  const c4 = base("IO16450");
  Object.assign(c4, { status: "declined" as ClaimStatus, decision: "Declined", created: addDaysISO(today, -12), lodged_on: addDaysISO(today, -12), acknowledged_at: `${addDaysISO(today, -12)} 09:00:00` });
  c4.patient = { pas_id: "PAS-33902", given: "Tomasi", family: "Vaka", dob: "1988-09-14", nhi: "PLR5521", mobile: "021 700 4412", email: "", address: "88 Rata Street, Christchurch 8011" };
  c4.employment = { status: "Employee", occupation: "Courier driver", employer: "FastParcel NZ" };
  c4.accident = { adate: addDaysISO(today, -12), atime: "07:50", location: "Christchurch City", scene: "Road", workplace: "No", vehicle: "Yes", sporting: "No", sport: "", cause: "rear-ended at traffic lights – neck pain" };
  c4.consent = { given: true, at: "(recorded)" };
  c4.diagnoses = [dx("44465007", "Sprain of neck", "N/A", true, "declined", true)];
  c4.declaration = { made: true, date: "(signed)", by: "Dr A. Rangi", provider_no: "HP-44921" };

  // 5) EXPIRED — outside the 14-day window; read-only / archived.
  const c5 = base("IO16445");
  Object.assign(c5, { status: "accepted" as ClaimStatus, decision: "Accepted", created: addDaysISO(today, -16), lodged_on: addDaysISO(today, -16), acknowledged_at: `${addDaysISO(today, -16)} 09:00:00` });
  c5.patient = { pas_id: "PAS-21847", given: "Grace", family: "Wilson", dob: "1962-01-30", nhi: "QDF3390", mobile: "027 118 2244", email: "", address: "3 Miro Place, Christchurch 8042" };
  c5.employment = { status: "Retired", occupation: "", employer: "" };
  c5.accident = { adate: addDaysISO(today, -16), atime: "11:15", location: "Christchurch City", scene: "Home", workplace: "No", vehicle: "No", sporting: "No", sport: "", cause: "tripped on a rug – landed on right wrist" };
  c5.consent = { given: true, at: "(recorded)" };
  c5.diagnoses = [dx("20946005", "Fracture of distal radius (wrist)", "Right", true, "accepted", true)];
  c5.declaration = { made: true, date: "(signed)", by: "Dr A. Rangi", provider_no: "HP-44921" };

  // 6) COLLEAGUE's claim at the same practice — sits in the practice pool until you open it.
  const c6 = base("IO16448");
  Object.assign(c6, { status: "draft" as ClaimStatus, created: addDaysISO(today, -1), created_by: "Dr K. Mere" });
  c6.encounter = { ...c6.encounter, provider: "Dr K. Mere (GP)" };
  c6.patient = { pas_id: "PAS-60455", given: "Peter", family: "Nabou", dob: "1985-03-11", nhi: "JHW4472", mobile: "021 555 8890", email: "", address: "40 Totara Street, Christchurch 8024" };
  c6.employment = { status: "Employee", occupation: "Electrician", employer: "Voltec Ltd" };
  c6.accident = { adate: "2026-07-08", atime: "10:30", location: "Christchurch City", scene: "Work", workplace: "Yes", vehicle: "No", sporting: "No", sport: "", cause: "cut left hand on a stripped wire while pulling cable" };
  c6.consent = { given: true, at: "08/07/2026 10:55" };
  c6.diagnoses = [dx("262911006", "Laceration of finger", "Left", true, "draft", true)];

  return [c0, c2, c1, c4, c3, c5, c6];
}

/** Synthesise an attributed, multi-author audit trail so the audit view has history. */
export function seedHistory(claims: Claim[]) {
  for (const c of claims) {
    if (persistence.hasHistory(c.reference)) continue;
    const creator = c.created_by;
    persistence.save(c, creator, creator.startsWith("Dr") ? "clinical" : "clerical", "claim created");
    if (c.consent.given) persistence.save(c, "R. Patel", "clerical", "patient details & consent recorded");
    if (c.diagnoses.length) persistence.save(c, "Dr A. Rangi", "clinical", "diagnoses & clinical assessment added");
    if (c.declaration.made) persistence.save(c, "Dr A. Rangi", "clinical", "Part E declaration signed");
    if (["lodged", "accepted", "held", "declined"].includes(c.status))
      persistence.save(c, "Dr A. Rangi", "clinical", "lodged ACC45");
    if (c.decision && ["Accepted", "Held", "Declined"].includes(c.decision))
      persistence.save(c, "ACC (system)", "acc", `ACC decision: ${c.decision}`);
  }
}
