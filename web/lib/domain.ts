// Pure domain logic — ported 1:1 from the Streamlit build (app.py).
// No framework dependencies: these are the rules, and they outlive the UI.

import type { Capacity, Claim, ClaimStatus, Diagnosis } from "./types";
import { nhi as nhiConnector } from "./connectors";

export const EDIT_WINDOW_DAYS = 14; // post-lodgement update/revision/repair window
export const LODGE_LIMIT_DAYS = 365; // ACC considers claims lodged within ~12 months

export const PRACTICE_FACILITY = "Riverside Medical Centre";

export const EMP_STATUSES = [
  "Not employed in NZ",
  "Retired",
  "Employee",
  "Self-employed",
  "Owner employee",
  "Other",
];

export const SCENES = ["Home", "Work", "Road", "Sports facility", "School", "Other"];

export const EXERTION = ["", "Sedentary", "Light", "Medium", "Heavy", "Very heavy"];

export const CAPACITY_STATES: Capacity[] = ["", "Fully fit", "Fit for selected work", "Fully unfit"];

export const CERT_TYPES = ["ACC45 initial (≤14 days)", "ACC18 (beyond 14 days)"];

export const SPORTS = [
  "Aerobics", "Athletics", "Badminton", "Basketball", "Boating", "Bowls", "Boxing",
  "Cricket", "Cycling", "Dancing", "Diving", "Equestrian", "Fishing", "Football (soccer)",
  "Golf", "Gymnastics", "Hockey", "Martial arts", "Motor sport", "Mountaineering",
  "Netball", "Rugby league", "Rugby union", "Running", "Sailing", "Skiing/snowboarding",
  "Squash", "Surfing", "Swimming", "Tennis", "Touch", "Tramping", "Volleyball",
  "Weightlifting", "Other",
];

export const STATUS_LABEL: Record<ClaimStatus, { cls: string; label: string }> = {
  draft: { cls: "pill", label: "Draft" },
  ready: { cls: "pill blue", label: "Ready to lodge" },
  lodged: { cls: "pill blue", label: "Lodged" },
  accepted: { cls: "pill ok", label: "Accepted" },
  held: { cls: "pill warn", label: "Held" },
  declined: { cls: "pill err", label: "Declined" },
};

// ---------------------------------------------------------------- dates

export function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Whole days between two ISO dates (a - b), UTC-normalised to avoid DST drift. */
export function daysBetween(a: string, b: string): number {
  const MS = 86_400_000;
  return Math.round((Date.parse(a + "T00:00:00Z") - Date.parse(b + "T00:00:00Z")) / MS);
}

export function addDaysISO(iso: string, days: number): string {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

// ---------------------------------------------------- 14-day repair window

export function isSubmitted(c: Claim): boolean {
  return ["lodged", "accepted", "held", "declined"].includes(c.status);
}

/** Days left in the 14-day POST-LODGEMENT window. null for unsubmitted drafts. */
export function daysLeft(c: Claim): number | null {
  if (!c.lodged_on) return null;
  return EDIT_WINDOW_DAYS - daysBetween(todayISO(), c.lodged_on);
}

export function isExpired(c: Claim): boolean {
  const d = daysLeft(c);
  return d !== null && d <= 0;
}

export function daysSinceAccident(c: Claim): number | null {
  return c.accident.adate ? daysBetween(todayISO(), c.accident.adate) : null;
}

/** Referral the user should act on: unfinished draft, or an ACC decision to address. */
export function needsRepair(c: Claim): boolean {
  return ["draft", "held", "declined"].includes(c.status);
}

// ------------------------------------------------------------- readiness

export type ReadinessCode = "admin" | "clinician" | "ready";

/**
 * For an unsubmitted claim, what's the next step to lodge?
 * Admin gaps take priority — they come first in the flow.
 */
export function readiness(c: Claim): { code: ReadinessCode; label: string; cls: string } {
  const { patient: p, accident: a, capacity: cap, declaration: dec } = c;
  const adminMissing =
    !p.given ||
    !p.family ||
    !p.dob ||
    !a.adate ||
    !a.cause.trim() ||
    !c.consent.given ||
    (a.sporting === "Yes" && !a.sport);

  const eligible = c.diagnoses.filter((d) => d.acc);
  const clinMissing =
    c.diagnoses.length === 0 ||
    eligible.length === 0 ||
    c.diagnoses.some((d) => !d.side) ||
    (cap.state === "Fit for selected work" && !cap.restrictions.trim()) ||
    (cap.state === "Fully unfit" && !cap.justification.trim()) ||
    !dec.made ||
    !dec.provider_no;

  if (adminMissing) return { code: "admin", label: "Clerical step needed", cls: "warn" };
  if (clinMissing) return { code: "clinician", label: "Clinician info needed", cls: "blue" };
  return { code: "ready", label: "Ready to lodge", cls: "ok" };
}

// ------------------------------------------------------------ validation

export interface ValidationResult {
  errors: string[];
  warnings: string[];
  canLodge: boolean;
}

export function validate(c: Claim): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  const { patient: p, accident: a, capacity: cap } = c;

  if (!p.given || !p.family) errors.push("Patient name is required.");
  if (!p.dob) errors.push("Date of birth is required.");
  if (!a.adate) errors.push("Accident date is required.");
  if (!a.cause.trim()) errors.push("Cause of injury is required.");
  if (a.sporting === "Yes" && !a.sport) errors.push("Select the sport for the sporting injury.");
  if (!c.consent.given) errors.push("Patient consent (all three authorisations) must be recorded.");
  if (c.diagnoses.length === 0) errors.push("At least one injury diagnosis is needed.");

  const eligible = c.diagnoses.filter((d) => d.acc);
  if (c.diagnoses.length > 0 && eligible.length === 0)
    errors.push("At least one ACC-eligible diagnosis is required to lodge.");
  for (const d of c.diagnoses) {
    if (!d.side) errors.push(`Diagnosis "${d.display}" needs a body side (or N/A).`);
  }
  if (cap.state === "Fit for selected work" && !cap.restrictions.trim())
    errors.push("Fit for selected work requires restrictions/activities.");
  if (cap.state === "Fully unfit" && !cap.justification.trim())
    errors.push("Fully unfit requires a justification.");
  if (!c.declaration.made)
    errors.push("Practitioner declaration (Part E) must be completed by an eligible signer.");
  if (!c.declaration.provider_no) errors.push("Provider number is required.");

  if (!p.nhi) warnings.push("No NHI supplied — slows processing.");
  else if (!nhiConnector.validate(p.nhi))
    warnings.push("NHI format looks invalid (real check-character validation is via the NHI service).");
  if (!p.mobile) warnings.push("No mobile — patient won't get an SMS decision.");
  const since = daysSinceAccident(c);
  if (since !== null && since >= LODGE_LIMIT_DAYS)
    warnings.push("Accident was over 12 months ago — delayed lodgement needs supporting clinical records.");

  return { errors, warnings, canLodge: errors.length === 0 };
}

// ------------------------------------------------------------ misc utils

export function uid(): string {
  const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
  let s = "";
  for (let i = 0; i < 7; i++) s += chars[Math.floor(Math.random() * chars.length)];
  return s;
}

export function fullName(c: Claim): string {
  return `${c.patient.given} ${c.patient.family}`.trim();
}

export function eligibleDx(c: Claim): Diagnosis[] {
  return c.diagnoses.filter((d) => d.acc);
}
