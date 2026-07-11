/**
 * Integration seams to external systems. Every external boundary is stubbed here and
 * documented with the real Health NZ service it stands in for. Going live means
 * implementing the real client inside a connector; the UI should not need to change.
 *
 * Ported from connectors.py. See PRODUCTION-READINESS.md for the gap analysis.
 */

import type { Claim, ClaimVersion, AuditEvent, Role, CoverDecision } from "./types";

export const CONNECTOR_MODE: Record<string, string> = {
  auth: "stub",
  nhi: "stub",
  hpi: "stub",
  pms: "stub",
  sdhr: "stub",
  terminology: "stub",
  acc: "stub",
  audit: "stub (in-memory)",
  persistence: "stub (in-memory)",
  notification: "stub (no-op)",
};

// ---------------------------------------------------------------------------
// 1. AUTH — workforce sign-in, identity and role/scope authorisation
//    REAL: My Health Account Workforce (OIDC). The role switcher is DEV-ONLY.
// ---------------------------------------------------------------------------
export interface AppUser {
  name: string;
  role_label: string;
  role_key: Role;
  can_edit_admin: boolean;
  can_edit_clinical: boolean;
  can_submit: boolean;
  can_sign_part_e: boolean;
  is_audit: boolean;
}

const ROLES: Record<Role, Omit<AppUser, "role_key">> = {
  clerical: {
    name: "R. Patel",
    role_label: "Clerical / Reception",
    can_edit_admin: true,
    can_edit_clinical: false,
    can_submit: false,
    can_sign_part_e: false,
    is_audit: false,
  },
  clinical: {
    name: "Dr A. Rangi",
    role_label: "Clinician",
    can_edit_admin: true,
    can_edit_clinical: true,
    can_submit: true,
    can_sign_part_e: true,
    is_audit: false,
  },
  audit: {
    name: "M. Chen",
    role_label: "Audit / Review",
    can_edit_admin: false,
    can_edit_clinical: false,
    can_submit: false,
    can_sign_part_e: false,
    is_audit: true,
  },
};

export const auth = {
  currentUser(role: Role): AppUser {
    return { ...ROLES[role], role_key: role };
  },
  canSignPartE: (role: Role) => ROLES[role].can_sign_part_e,
  canSubmit: (role: Role) => ROLES[role].can_submit,
  canEditAdmin: (role: Role) => ROLES[role].can_edit_admin,
  canEditClinical: (role: Role) => ROLES[role].can_edit_clinical,
  isAudit: (role: Role) => ROLES[role].is_audit,
};

// ---------------------------------------------------------------------------
// 2. NHI — National Health Index
//    REAL: NHI FHIR API (Digital Services Hub). STUB: regex format check only.
//    Production must add HISO 10046 check-character validation.
// ---------------------------------------------------------------------------
const NHI_LEGACY = /^[A-HJ-NP-Z]{3}\d{4}$/; // AAANNNN
const NHI_NEW = /^[A-HJ-NP-Z]{3}\d{2}[A-HJ-NP-Z]{2}$/; // AAANNAA (letters exclude I, O)

export const nhi = {
  validate(value: string): boolean {
    if (!value) return false;
    const v = value.trim().toUpperCase();
    return NHI_LEGACY.test(v) || NHI_NEW.test(v);
  },
  lookup(_value: string): null {
    return null; // STUB — no demographics lookup offline
  },
};

// ---------------------------------------------------------------------------
// 3. HPI — provider / facility identity.  REAL: HPI FHIR API.
// ---------------------------------------------------------------------------
export const hpi = {
  defaultProviderNumber: () => "HP-44921",
};

// ---------------------------------------------------------------------------
// 4. PMS/PAS — encounter (visit) launch context.  REAL: SMART on FHIR EHR launch.
// ---------------------------------------------------------------------------
export const pms = {
  getEncounterContext() {
    return {
      encounter: {
        external_id: "ENC-" + Math.floor(100000 + Math.random() * 900000),
        source: "pms_context",
        facility: "Riverside Medical Centre",
        provider: "Dr A. Rangi (GP)",
        klass: "Outpatient / GP consult",
        source_system: "Medtech PMS (STUB)",
      },
      patient: {
        pas_id: "PAS-88213",
        given: "Margaret",
        family: "Ellery",
        dob: "1949-03-11",
        nhi: "JBX4728",
        mobile: "021 555 0192",
        email: "",
        address: "14 Rewi Street, Christchurch 8022",
      },
    };
  },
};

// ---------------------------------------------------------------------------
// 5. TERMINOLOGY — SNOMED CT NZ Edition + ACC claim reference set
//    REAL: NZHTS/Ontoserver ValueSet/$expand + $validate-code, bound to
//    acc-claim-reference-set (11,917 concepts). STUB: 15-concept sample.
// ---------------------------------------------------------------------------
export interface Concept {
  code: string;
  display: string;
  site: string;
  acc: boolean;
}

const CONCEPTS: Concept[] = [
  { code: "283384001", display: "Sprain of ligament of ankle", site: "Ankle", acc: true },
  { code: "262911006", display: "Laceration of finger", site: "Finger", acc: true },
  { code: "20946005", display: "Fracture of distal radius (wrist)", site: "Wrist", acc: true },
  { code: "82576008", display: "Contusion of knee", site: "Knee", acc: true },
  { code: "209815008", display: "Sprain of rotator cuff (shoulder)", site: "Shoulder", acc: true },
  { code: "312608009", display: "Laceration - injury", site: "", acc: true },
  { code: "110030002", display: "Concussion injury of brain", site: "Head", acc: true },
  { code: "125605004", display: "Fracture of bone", site: "", acc: true },
  { code: "44465007", display: "Sprain of neck", site: "Neck", acc: true },
  { code: "81680005", display: "Closed fracture of shaft of tibia", site: "Lower leg", acc: true },
  { code: "7200002", display: "Alcohol dependence syndrome", site: "", acc: false },
  { code: "73211009", display: "Diabetes mellitus", site: "", acc: false },
  { code: "38341003", display: "Hypertensive disorder", site: "", acc: false },
  { code: "48694002", display: "Anxiety disorder", site: "", acc: false },
  { code: "183932001", display: "Presentation for social reasons", site: "", acc: false },
];

export const terminology = {
  VALUESET_VERSION: "20260401 (STUB)",
  /** FHIR ValueSet/$expand equivalent (typeahead). */
  search(query = "", eligibleOnly = true): Concept[] {
    let pool = CONCEPTS.filter((c) => c.acc || !eligibleOnly);
    const q = query.trim().toLowerCase();
    if (q) pool = pool.filter((c) => c.display.toLowerCase().includes(q) || c.code.includes(q));
    return pool;
  },
  /** FHIR $validate-code equivalent against the ACC claim reference set. */
  isAccEligible(code: string): boolean {
    return CONCEPTS.some((c) => c.code === code && c.acc);
  },
};

// ---------------------------------------------------------------------------
// 6. ACC — number allocation, lodgement, cover-status polling
//    REAL: ACC Developer Resource Centre (developer.acc.co.nz), integrated directly —
//    this app is the ACC software vendor, not proxied via the PMS. Claim Number
//    Allocation API (numbers), Claim API (lodge ACC45/ACC18), Query Claim Status API
//    (poll registration + cover decision — no webhook). Auth = API key + Health Secure
//    Digital Certificate; compliance (test) env precedes prod. See PRODUCTION-READINESS.md F.
// ---------------------------------------------------------------------------
export const acc = {
  /** Opaque string; three ACC formats (AB12345 / 12345AB / 1234ABC) — do not parse. */
  allocateClaimNumber: (seq: number) => "IO" + seq,

  /**
   * Submit the ACC45. Returns a **transport-level acknowledgement** — the message
   * reached ACC — after which ACC registers the claim. This is NOT a cover decision:
   * ACC's documented cover statuses are accept / decline / held (held = under review),
   * plus "not applicable" while the claim is not yet registered. A cover decision is
   * obtained by **polling** the Query Claim Status API and lands in `Claim.decision`.
   */
  lodge: (_claim: Claim): string => nowStamp(),

  /** Cover decision, obtained by polling ACC's Query Claim Status API. STUB: button. */
  decision: (choice: CoverDecision): CoverDecision => choice,
};

// ---------------------------------------------------------------------------
// 7/8. AUDIT + PERSISTENCE — append-only, attributed history
//    REAL: NZ-region datastore with RLS; append-only audit (FHIR AuditEvent).
//    Production must add optimistic locking — see PRODUCTION-READINESS.md §G.
// ---------------------------------------------------------------------------
const AUDIT_LOG: AuditEvent[] = [];
const VERSIONS: Record<string, ClaimVersion[]> = {};

function nowStamp(): string {
  return new Date().toISOString().slice(0, 19).replace("T", " ");
}

export const audit = {
  record(author: string, role: string, action: string, reference = "", detail = "") {
    AUDIT_LOG.push({ ts: nowStamp(), author, role, action, reference, detail });
  },
  history: (reference: string) => AUDIT_LOG.filter((e) => e.reference === reference),
  all: () => AUDIT_LOG.slice(),
};

export const persistence = {
  /** One save → one attributed claim_version row + one audit_event. */
  save(claim: Claim, author: string, role: string, action: string): number {
    const ref = claim.reference;
    const v = (VERSIONS[ref]?.length ?? 0) + 1;
    (VERSIONS[ref] ??= []).push({ version: v, ts: nowStamp(), author, role, action });
    audit.record(author, role, action, ref, `v${v}`);
    return v;
  },
  versions: (reference: string): ClaimVersion[] => VERSIONS[reference] ?? [],
  hasHistory: (reference: string) => (VERSIONS[reference]?.length ?? 0) > 0,
};

// ---------------------------------------------------------------------------
// 9. NOTIFICATION — outbound SMS/email (ACC decision SMS to the patient)
// ---------------------------------------------------------------------------
export const notification = {
  sendDecisionSms: (_mobile: string, _reference: string, _decision: string) => false,
};
