// Claim aggregate — mirrors the Streamlit build's dict shape and DATABASE-SCHEMA.md.
// Dates are ISO "YYYY-MM-DD" strings (or null) so state stays JSON-serialisable.

export type Role = "clerical" | "clinical" | "audit";

export type ClaimStatus = "draft" | "ready" | "lodged" | "accepted" | "held" | "declined";

/**
 * ACC's cover decision. Per ACC's ProviderHub, a claim's cover status is
 * accept / decline / held (held = under review, "pre-cover"). There is NO
 * "Received" cover decision — an eLodgement acknowledgement is a transport-level
 * receipt, not a determination, and is recorded on `Claim.acknowledged_at`.
 */
export type CoverDecision = "Accepted" | "Held" | "Declined";

export type YesNo = "Yes" | "No";

export type Capacity = "" | "Fully fit" | "Fit for selected work" | "Fully unfit";

export interface Encounter {
  external_id: string;
  source: string;
  facility: string;
  provider: string;
  klass: string;
  source_system: string;
}

export interface Patient {
  pas_id: string;
  given: string;
  family: string;
  dob: string;
  nhi: string;
  mobile: string;
  email: string;
  address: string;
}

export interface Employment {
  status: string;
  occupation: string;
  employer: string;
}

export interface Accident {
  adate: string | null;
  atime: string;
  location: string;
  scene: string;
  workplace: YesNo;
  vehicle: YesNo;
  sporting: YesNo;
  sport: string;
  cause: string;
}

export interface Consent {
  given: boolean;
  at: string | null;
}

export interface Diagnosis {
  id: string;
  code: string;
  display: string;
  site: string;
  side: string;
  acc: boolean;
  primary: boolean;
  status: string;
  source_request?: string;
}

export interface Flags {
  gradual: YesNo;
  treatment: YesNo;
  admitted: YesNo;
  home: YesNo;
}

export interface CapacityRecord {
  exertion: string;
  state: Capacity;
  restrictions: string;
  justification: string;
  cert_type: string;
  valid_from: string | null;
  valid_to: string | null;
}

export interface Declaration {
  made: boolean;
  date: string | null;
  by: string | null;
  provider_no: string;
}

export interface ChangeRequest {
  id: string;
  kind: "add" | "change" | "correct";
  code: string;
  display: string;
  side: string;
  acc: boolean;
  same_event: boolean;
  bundled: string;
  reason: string;
  status: string;
}

export interface Claim {
  id: string;
  reference: string;
  number_source: string;
  status: ClaimStatus;
  /** ACC's cover decision. Null until ACC issues one — lodging does not set it. */
  decision: CoverDecision | null;
  /** Transport-level eLodgement receipt ("your message reached ACC"). Not a decision. */
  acknowledged_at: string | null;
  created: string;
  created_by: string;
  lodged_on: string | null;
  encounter: Encounter;
  patient: Patient;
  employment: Employment;
  accident: Accident;
  consent: Consent;
  diagnoses: Diagnosis[];
  flags: Flags;
  capacity: CapacityRecord;
  declaration: Declaration;
  change_requests: ChangeRequest[];
}

/** One append-only, attributed snapshot of a claim (see DATABASE-SCHEMA.md claim_version). */
export interface ClaimVersion {
  version: number;
  ts: string;
  author: string;
  role: string;
  action: string;
}

export interface AuditEvent {
  ts: string;
  author: string;
  role: string;
  action: string;
  reference: string;
  detail: string;
}
