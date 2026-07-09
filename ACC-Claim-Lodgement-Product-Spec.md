# ACC Claim Lodgement — Product Specification

**Working title:** ACC Claim Console
**Purpose:** A two-role web application for lodging and maintaining New Zealand ACC injury claims (ACC45) and medical certificates (ACC18), split into an **administrative interface** for patient/claim logistics and a **clinician interface** for clinical assessment, diagnosis, work capacity certification, and practitioner attestation.
**Status:** Draft v1 — intended as the build brief for a Claude Code mockup.
**Date:** 8 July 2026

---

## 1. Background & scope

New Zealand's Accident Compensation Corporation (ACC) provides no-fault injury cover. To trigger cover and entitlements, a registered health provider lodges an **ACC45 Injury Claim** on the patient's behalf. When incapacity extends past the initial period, the provider issues an **ACC18 Medical Certificate**. This product digitises those two forms and the surrounding workflow.

The reference screenshot (a PMS-style ACC lodgement screen) shows the domain we are modelling: accident details, a triage/cause-of-injury narrative, a coded diagnosis grid with body side and an "ACC?" eligibility flag, employment and work-exertion fields, patient consent, and a medical practitioner declaration with a "Complete" action that lodges the claim.

**In scope**

- Administrative interface: create/open claims, capture and maintain patient demographics, NHI, contact and employer details, accident logistics, consent record, employment status.
- Clinician interface: coded diagnoses (with body site/side and ACC-eligibility), gradual-process / treatment-injury / admission flags, rehabilitation and home-assistance requests, work-capacity certification (ACC45 initial certificate and ACC18), and the practitioner declaration/attestation.
- Shared claim record, validation, lodgement, and status tracking.

**Out of scope (v1)**

Direct electronic submission to ACC's backend (we model it as a `lodge` action with a stubbed response), invoicing/payment, dentist ACC42 flow, accidental-death ACC21, and the Sensitive Claims Service client engagement form. These are noted as future extensions where relevant.

### 1.1 Mapping to the ACC45 paper/electronic form

The ACC45 is organised into five parts. The two interfaces divide responsibility across them:

| ACC45 Part | Contents | Owned by |
|---|---|---|
| A — Personal details | Name, DOB, NHI, address, contact | Administrative |
| B — Accident & employment | Date/time/place of accident, cause, employer, employment status | Administrative (with clinician-relevant flags surfaced to clinician) |
| C — Injury diagnosis & assistance | Coded diagnoses, body site/side, gradual process, treatment injury, rehab/home assistance | Clinician |
| D — Ability to work | Work capacity, restrictions, certificate period | Clinician |
| E — Treatment provider & patient declaration | Provider number, practitioner declaration, patient consent | Split: consent captured by Administrative; declaration signed by Clinician |

> **Constraint:** ACC45 Part E's *practitioner declaration* can only be completed by a **doctor or nurse practitioner**. The form can be lodged without it, but weekly-compensation-relevant certification and treatment-injury lodgement depend on an eligible signer.

---

## 2. Users & roles

**Administrator / Practice reception (`admin`)**
Opens claims, enters and verifies patient identity and contact details, records employer information, captures accident logistics, and records the patient's consent. Cannot add clinical diagnoses or sign the practitioner declaration.

**Clinician — GP / Nurse Practitioner / Medical Specialist (`clinician_prescriber`)**
Full clinical rights: add/edit diagnoses, set flags, request rehabilitation, certify work capacity, issue ACC18, and complete the practitioner declaration (Part E).

**Clinician — allied / limited scope, e.g. physiotherapist, nurse (`clinician_limited`)**
Can add diagnoses and clinical notes within their scope and lodge certain claim types, but **cannot** complete Part E declaration or certify weekly-compensation certificates. The UI must hide/disable those controls and show why.

**System/admin (`sysadmin`)** — provider registry, value-set refresh, audit access. (Configuration only; not a primary workflow persona.)

Permissions are enforced server-side; the UI mirrors them by disabling and annotating controls rather than hiding them silently, so users understand *why* an action is unavailable.

---

## 3. End-to-end workflow

```
Patient presents
      │
      ▼
[PAS/PMS] Encounter (visit) created ──► patient + provider + facility + visit period
      │                                  (system of record for identity)
      ▼
[ADMIN] Launch claim console in encounter context
      │      ► allocate a new ACC45 number (from pre-allocated block or ACC API)
      │      ► claim bound to the PAS/PMS encounter; patient details inherited, not re-keyed
      ▼
[ADMIN] Create / open claim ──► verify identity, NHI, contact, employer
      │                          record accident logistics (date, time, place, scene, cause)
      │                          record patient consent (3-question script)
      ▼
[CLINICIAN] Clinical assessment
      │      add coded diagnosis/es (injury + body site + side + ACC? flag)
      │      set flags: gradual process, treatment injury, admitted, home assistance
      │      request rehabilitation / ACC1 if needed
      │      certify ability to work (fully fit / fit for selected work / fully unfit)
      │      issue initial certificate (≤14 days) and/or ACC18 (beyond 14 days)
      │      complete practitioner declaration (Part E)  ◄── prescriber only
      ▼
[SYSTEM] Validation gate (all mandatory fields, ≥1 diagnosis, eligible signer)
      │
      ▼
[SYSTEM] Lodge claim ──► ACC (stubbed) ──► decision status (Received / Accepted / Held / Declined)
      │
      ▼
[ONGOING] Update claim, add ACC18 recertifications, change diagnoses, amend details
```

Key handoffs:

- **Admin → Clinician** is a soft handoff: both can work concurrently on the same claim record. The clinician view shows a read-only summary of the accident/consent context the admin captured, and flags anything missing.
- **Lodgement gate** is the hard gate. The `Complete`/`Lodge` action is disabled until validation passes and an eligible signer has attested (for claim types that require it).
- **Recertification loop:** after lodgement, a clinician can issue additional ACC18 certificates against the same claim, each with its own capacity determination and validity period.

---

## 4. Administrative interface — functionality

### 4.0 Encounter context & ACC number allocation (PAS/PMS integration)

The claim does not exist in isolation — it is tied to a **clinical encounter (the visit)** owned by the practice's **Patient Administration System (PAS) or Patient Management System (PMS)**, which is the system of record for patient identity and the visit. Two entry modes:

- **Launched-in-context (primary):** the console is opened from the PAS/PMS against an existing encounter. The launch passes encounter context — encounter id, patient (with NHI and demographics), attending provider, and facility/location. Patient details are **inherited read-mostly** from the PAS; the admin verifies rather than re-keys, and corrections flow back to the PAS where possible.
- **Standalone:** the console creates or looks up an encounter itself (patient search by NHI/name, new-visit creation), for practices without an integrated PAS.

**Tie the whole claim/visit to the encounter.** The `Claim`, and every artifact hanging off it (diagnoses, certificates/ACC18, diagnosis-change requests, attachments), carry the `encounterId`. This gives one clinical thread per visit: the encounter supplies visit date/time, provider, and location; the claim supplies the ACC-specific overlay. Modelled on FHIR **`Encounter`** (subject → Patient, participant → Practitioner, serviceProvider → Organization/facility, period, location).

**Creating a new ACC45 number.** Every claim reserves a unique **ACC45 claim number** at creation (shown as the Claim reference, e.g. `IO16456` in the reference screenshot). Support both allocation sources:

- **Pre-allocated block** — the practice/PMS holds a sequence of ACC45 numbers issued by ACC; the console draws the **next unused** number and marks it consumed. Track the remaining pool with a low-watermark warning and a "request more numbers" prompt.
- **On-demand via ACC's Claim Number Allocation API** — request a fresh number at claim creation, removing the need to hold/refill blocks. Prefer this when available; fall back to the local block if the API is unavailable.

Rules:
- The number is **reserved at claim creation** (a draft has a number, matching the screenshot), **committed on lodgement**, and voided/returned if a draft is abandoned per practice policy — never silently reused.
- Store the number as an **opaque string and validate against ACC's current allocation rules — do not hard-code prefix/length**: ACC is changing the ACC45 number format as the legacy pool is exhausted, so format assumptions will break.
- Guarantee uniqueness across providers; guard against duplicate allocation.

### 4.1 Claim header & lifecycle
- Display **Claim reference number** (the allocated ACC45 number, e.g. `IO16456`); show claim status badge (Draft, Ready to lodge, Lodged, Accepted, Held, Declined) and the linked encounter/visit.
- Create new claim (allocates a number per §4.0); search/open existing claim by reference, NHI, patient name, or encounter id.
- Duplicate-claim warning if an open claim exists for the same patient + accident date, or for the same encounter.

### 4.2 Patient details (ACC45 Part A)
Editable fields with validation:
- Full legal name (given + family), preferred name.
- **Date of birth** (date picker; drives age-derived logic).
- **NHI number** — 7-character NHI, validated with the official NHI check-character algorithm; optional but strongly encouraged with an inline "improves processing speed" hint.
- Sex/gender, ethnicity (optional, for reporting).
- Residential + postal address (NZ address format; supports overseas address for visitors).
- Mobile phone and email (mobile enables ACC's SMS decision notification).
- "Verify spelling with patient" confirmation checkbox.

### 4.3 Employer & employment (ACC45 Part B)
- **Employment status:** Not employed in NZ / Retired / Employee / Self-employed / Owner employee / Other (single-select; mirrors screenshot).
- **Occupation** free-text (auto-set to "Unemployed"/disabled when Not employed in NZ).
- **Employer name, address, contact** — required when status is Employee; used for the employer notification letter.
- **Accredited Employer (AE) detection:** flag/lookup indicating the employer manages its own claims via a TPA; if set, surface routing guidance (send forms/invoices to AE/TPA, not ACC).

### 4.4 Accident logistics (ACC45 Part B)
- **Date & time of accident** (must be ≤ now; relative "X hours ago" helper as in screenshot).
- **Geographic location** (town/city) and **country** (defaults NZ; overseas allowed with follow-up note).
- **Accident scene** (Home, Work, Road, Sports facility, School, Other — select).
- **Workplace accident?** Yes/No.
- **Involved a moving vehicle on a public road?** Yes/No (drives motor-vehicle-injury handling).
- **Sporting injury?** Yes/No.
- **Cause of injury** free-text describing the mechanism (e.g. "walking through to the kitchen – tripped over own feet – fallen to ground"). Required.
- **Triage/assessment narrative** free-text (clinical context captured at intake; read-only to admin after clinician edits).

### 4.5 Consent (ACC45 Part E — patient portion)
- Structured capture of the **three-question consent script** (records collection/use/disclosure authorisation; true-and-correct declaration; authority to lodge). Each recorded as an explicit Yes with timestamp and the staff member who captured it.
- Show a "Patient Consent — Given on DD/MM/YYYY" confirmation banner (as in screenshot) once complete.
- Support authorised-representative consent (capture representative name/relationship) when the patient cannot consent directly.

### 4.6 Admin validation & readiness
- Live checklist of missing mandatory Part A/B fields.
- Cannot mark "Ready for clinician" until identity + accident date + cause + consent are present.

---

## 5. Clinician interface — functionality

### 5.1 Context summary (read-only)
Compact panel showing patient identity, accident date/scene, cause-of-injury, and consent status the admin captured — so the clinician has full context without leaving the screen. Missing items are flagged with a jump-link back to admin.

### 5.2 Diagnosis grid (ACC45 Part C) — core feature
A repeatable grid; **at least one injury diagnosis is required** to lodge (mirrors the screenshot's "At least one injury diagnosis is needed" error). Each row:

- **Diagnosis** — coded, selected from a terminology-bound picker (see §7). Must be a specific injury (e.g. "sprain", "open wound", "contusion") plus **body site** (e.g. "blister of toe", not "blister"), not a symptom.
- **Side** — Left / Right / Bilateral / Not applicable.
- **ACC? (eligibility)** — whether the coded concept is claimable under ACC. Auto-derived from the ACC claim reference value set (§7): concepts that are members → Yes; concepts outside the set → No (e.g. "Presentation for social reasons" → No). Non-claimable rows are allowed for the record but do not satisfy the lodgement rule below.
- Add / edit / delete rows; primary-diagnosis designation.
- Coding system indicator (Read code / SNOMED CT / ICD-10) per row.

#### 5.2.1 ACC-eligibility feedback (must be explicit and immediate)

Clinicians should never discover at submit time that nothing they entered qualifies. Eligibility is resolved and surfaced **at the moment a diagnosis is selected**, not only at lodgement:

- **On select**, resolve membership against the ACC claim reference set (via `$validate-code`, or locally against the cached member codes — see §7). Set the row's ACC? flag from the result.
- **When a selected SNOMED/Read/ICD code does not qualify**, the row is visibly marked **"Not ACC-eligible"** (distinct styling + icon, not just an "N") with an inline explanation, e.g. *"This code isn't in the ACC claim reference set — it can be recorded but can't support an ACC claim on its own."* Where helpful, offer a nudge to pick a more specific injury concept (a symptom or social-reason code will not qualify; a specific injury + body site will).
- **Typeahead may optionally scope** to the ACC value set by default (so only claimable concepts appear), with a toggle to search the full terminology when the clinician deliberately needs to record a non-claimable diagnosis.
- The grid shows a persistent **eligibility summary**: e.g. "2 diagnoses · 1 ACC-eligible" and, when zero qualify, a prominent banner: **"No ACC-eligible diagnosis yet — add at least one to lodge this claim."**
- Every row still displays its resolved status so a mixed grid (some eligible, some not) is unambiguous.

### 5.3 Clinical flags (ACC45 Part C)
Yes/No controls with a "No to all" shortcut (as in screenshot):
- **Work-related gradual process?** — if Yes, requires medical practitioner and prompts for employment/work history; sets claim to complex/investigation path.
- **Is this claim for treatment injury?** — if Yes, triggers the **ACC2152** supplementary flow and a prompt to attach relevant patient notes.
- **Is home assistance required?** — if Yes, offers to attach an **ACC1 Request for assistance**.
- **Has the patient been admitted?** — Yes/No.
- (Extensible: sensitive claim, maternal birth injury — each with the correct coding/annotation guidance.)

### 5.4 Rehabilitation & support requests
- Toggle "Rehabilitation assistance required" and link an ACC1.
- Free-text clinical recommendation notes.

### 5.5 Ability to work / certification (ACC45 Part D + ACC18)
- **Normal work exertion:** Sedentary / Light / Medium / Heavy / Very heavy.
- **Work capacity determination:**
  - **Fully fit** — no restriction; "Yes – no further action".
  - **Fit for selected work** — patient can do some work; requires **specified activities/restrictions and the type of work** they can do.
  - **Fully unfit** — only where return to work would materially risk the patient's health or others' safety; requires justification.
- **Certificate type & period:**
  - **Initial certificate** on the ACC45 covers up to the **first 14 days**.
  - **ACC18** certifies **beyond 14 days**; supports issuing at the initial consult alongside the ACC45 and as later recertifications, each with a `valid from`/`valid to` range.
- Show downstream note: "fit for selected work" and "fully unfit" (with prior earnings) may make the patient eligible for weekly compensation — informational only, not a benefit determination.
- Handle "patient not employed in NZ": suppress/greys the return-to-work determination (as in screenshot).

### 5.6 Practitioner declaration / attestation (ACC45 Part E)
- Certification statements ("I have personally examined the patient…", "the condition is the result of an accident", "the patient/representative has signed the declaration and authorised me to lodge").
- **Declaration made** checkbox + **date of declaration** (with a "Today" quick-set).
- **Provider number** selection (use the number for the practice where lodging).
- **Eligible-signer enforcement:** only `clinician_prescriber` can complete this; for others the control is disabled with an explanation and an option to route to an eligible colleague.

### 5.7 Lodgement
- `Save & Close`, `Save`, `Complete` (lodge), `Print`, `Back` actions.
- `Complete` runs the validation gate (§6) and, on success, transitions the claim to Lodged and records the submission timestamp and submitter.

### 5.8 Post-lodgement diagnosis changes (add / change / correct)

Once an ACC45 is lodged, the diagnosis grid is **no longer freely editable** — the lodged rows are the record ACC used to make its cover decision. Further clinical changes during (and after) the initial 14-day window are handled as **explicit, reviewable requests against the existing claim**, not by re-lodging the ACC45. This mirrors ACC's real "Updating or changing a claim" process and is the primary flow to demonstrate in the mockup.

There are three distinct operations, each with different rules and UX:

**(a) Add a diagnosis** — a further injury found while treating the patient (e.g. treating a shoulder from a fall, later finding the knee was injured in the *same* fall). Allowed only when the new diagnosis **relates to the initial injury** and was **caused by the same accident/event** already on the ACC45. This is the flow the demo centres on. It is a **Change-in-Diagnosis request** carrying: diagnosis code + description, body site (and side), date of accident/event (pre-filled from the claim, read-only), and a short free-text reason for the addition. The request receives its **own cover decision** (Accepted / Held / Declined) independent of the original claim's decision.

**(b) Change a diagnosis** — replace a diagnosis, allowed when there was an administrative error (wrong code submitted) or new information confirms a different injury. Same request payload as (a), plus a reference to the diagnosis being superseded.

**(c) Fix a minor error** — e.g. wrong body side, or a typo in the accident date. In the real world these are corrected informally (phone/email to ACC registration). In the product, model them as a lightweight **correction request** distinct from a clinical diagnosis change, so they don't trigger a fresh cover assessment.

**How it's transacted.** Adds/changes are submitted through the "Change in diagnosis" function of the PMS (or an ACC32 on ProviderHub), and may be **bundled with a concurrent request for treatment/support** — most relevantly, **attached to the ACC18 medical certificate** the clinician issues in the same encounter. So in the initial window the typical action is: issue the ACC18 recertification **and** attach an "add diagnosis" request in one submission.

**UI behaviour on a lodged claim.**
- Lodged diagnosis rows render read-only with a status chip (Lodged / Change pending / Accepted / Declined).
- An **`Add / change diagnosis`** action opens a request drawer: terminology-bound picker (same as §5.2), body site/side, read-only accident date, reason text, and an optional "attach to ACC18" toggle.
- A same-event confirmation is required ("this injury was caused by the accident already on this claim") before submit; if the clinician indicates a *different* accident, the UI steers them to lodge a **new ACC45** instead.
- Submitting creates a pending change request and, on the stubbed ACC response, updates the target row's status. The original lodged record and every request are retained for audit — nothing is destructively overwritten.

> **Two kinds of "revision" — keep them separate.** The **ACC18 certificate series** (§5.5) revises *work-capacity certification* over time and does not change cover. A **diagnosis change request** (this section) revises *what injuries are covered* and always triggers an ACC cover assessment. They can travel together in one submission but are modelled as separate records.

---

## 6. Validation & business rules

Mandatory-to-lodge:
- Patient name + DOB present; NHI valid format if supplied.
- Accident date/time (≤ now), cause of injury, and accident scene present.
- Patient consent recorded (all three authorisations = Yes) with timestamp.
- **≥ 1 diagnosis**, and — **hard block** — **≥ 1 ACC-eligible diagnosis** (a member of the ACC claim reference set). If every diagnosis on the claim resolves to Not ACC-eligible, the `Complete`/lodge action is **disabled**, with the blocking reason stated inline (mirrors the screenshot's "At least one injury diagnosis is needed", extended to eligibility: *"At least one ACC-eligible diagnosis is required to lodge."*). Non-eligible-only claims can be saved as a draft but cannot be submitted. Eligibility is validated **server-side at lodge** as well as in the UI, so a stale client can't bypass the gate.
- Each diagnosis has a body side value (or explicit "Not applicable").
- If **Fit for selected work** → restrictions/activities text required.
- If **Fully unfit** → justification required.
- If **treatment injury = Yes** → ACC2152 flagged/attached before lodge (or explicit defer).
- If **gradual process = Yes** → signer must be a medical practitioner.
- For claim types requiring certification → Part E declaration completed by an eligible signer.
- Provider number selected.

Warnings (non-blocking): missing NHI, missing mobile (no SMS decision), missing employer for an employee, accident > 12 months ago (delayed-lodgement info requirement), overseas accident location.

---

## 7. Terminology & coding bindings

Diagnoses are coded, not free-text. The diagnosis picker is bound to standard NZ health terminology and to the **ACC claim reference set** for eligibility.

- **ACC claim reference value set** — `https://nzhts.digital.health.nz/fhir/ValueSet/acc-claim-reference-set` (NZ Health Terminology Service, FHIR R4 `ValueSet`, version `20260401`, status `draft`). Confirmed live: it is an **extensional** value set enumerating **11,917 SNOMED CT concepts** from the **SNOMED CT New Zealand Edition** (module `21000210109`, edition `20251001`) — the concepts recognised as ACC-claimable injury diagnoses. The application uses it two ways: (1) as the **bound value set for the diagnosis picker's typeahead** (so clinicians search and select valid injury concepts), and (2) to **auto-populate the "ACC?" flag** — a selected concept that is a member of the set resolves to ACC-eligible.
- **Resolution mechanism:** call `ValueSet/$expand` (typeahead search with `filter`) and `$validate-code` (confirm membership / drive the ACC? flag). **Important:** the public NZHTS endpoint is *definition-only* — it publishes the code membership but is **not provisioned to expand** (`$expand`/`$validate-code` return `404 not-found`: no SNOMED edition loaded). Displays and expansions require a terminology server (Ontoserver/Snowstorm) loaded with SNOMED CT NZ Edition. Because the set is extensional, the ACC? flag can also be resolved locally from a cached copy of the 11,917-code array. Pin and record `ValueSet.version` + SNOMED edition at lodgement for auditability. See the companion **ACC-FHIR-Terminology-Spec.md** for full detail.
- **Legacy/interop codes:** support Read codes and ICD-10 alongside SNOMED CT, since ACC accepts Read/SNOMED/ICD-10 depending on the source system; store the code, system URI, and display term per diagnosis.
- **Body site / side** are captured as structured attributes (ideally SNOMED laterality), not embedded in the diagnosis text.

> The value-set contents are served as FHIR JSON from the NZHTS endpoint above; the mockup can stub the expansion with a small representative sample (e.g. sprain, contusion, open wound, fracture — with body sites) plus one non-claimable example ("Presentation for social reasons") to demonstrate the ACC?-flag behaviour.

---

## 8. Data model (indicative)

```
Encounter                         // the visit; owned by / mirrored from PAS/PMS
  id, source (pas_context | pms_context | standalone), externalEncounterId,
  pasSystemId, patientId, attendingProviderId, facilityId, class,
  periodStart, periodEnd, location

Claim
  id, referenceNumber (allocated ACC45 number, opaque string),
  numberSource (preallocated_block | acc_allocation_api),
  encounterId (→ Encounter),        // whole claim/visit tied to the encounter
  status, createdAt, lodgedAt, submittedBy, providerNumber,
  claimType (injury | treatment_injury | gradual_process | sensitive | maternal_birth)

NumberPool                         // pre-allocated ACC45 block state (block mode)
  providerId, rangeStart, rangeEnd, nextUnused, remaining, lowWatermark

Patient
  claimId, pasPatientId, sourceSystem,   // identity sourced from PAS/PMS
  givenName, familyName, dob, nhi, sex, ethnicity,
  residentialAddress, postalAddress, mobile, email, consentVerified

Employment
  claimId, status, occupation, employerName, employerAddress, employerContact,
  accreditedEmployer (bool), tpaContact

Accident
  claimId, datetime, country, location, scene, workplaceAccident (bool),
  movingVehicleOnRoad (bool), sportingInjury (bool), causeOfInjury (text),
  triageNarrative (text)

Consent
  claimId, collectionAuth (bool), truthDeclaration (bool), lodgeAuth (bool),
  capturedBy, capturedAt, representativeName, representativeRelationship

Diagnosis (0..*)
  claimId, code, codeSystem (SNOMED|READ|ICD10), display, bodySite, side,
  accEligible (bool, derived), isPrimary (bool),
  status (draft | lodged | change_pending | accepted | declined | superseded),
  sourceRequestId (nullable → DiagnosisChangeRequest that created/changed this row),
  supersedesDiagnosisId (nullable)

DiagnosisChangeRequest (0..*)   // post-lodgement add / change / correct
  claimId, kind (add | change | correct),
  targetDiagnosisId (nullable; set for change/correct),
  code, codeSystem, display, bodySite, side,
  accidentDate (copied from claim; read-only),
  sameEventConfirmed (bool),      // must be true for clinical add/change
  reason (text),
  bundledWith (nullable → Certificate.id when attached to an ACC18),
  transport (change_in_diagnosis | ACC32 | correction),
  status (submitted | accepted | held | declined),
  requestedBy, requestedAt, decidedAt

ClinicalFlags
  claimId, gradualProcess, treatmentInjury, admitted, homeAssistance,
  rehabRequested

Certificate (0..*)
  claimId, type (ACC45_initial | ACC18), workExertionLevel,
  capacity (fully_fit | selected_work | fully_unfit),
  restrictions (text), justification (text), validFrom, validTo, issuedBy, issuedAt

Declaration
  claimId, declarationMade (bool), declarationDate, signedBy (must be prescriber)

Attachment (0..*)
  claimId, kind (ACC1 | ACC2152 | patient_notes | other), fileRef
```

---

## 9. Screens & states

**Screen 1 — Claim workspace (shared, tabbed or two-pane).** Left/main: the active form section; right rail: claim header, status, and validation checklist. The reference screenshot is essentially this screen with four cards (Accident Details, Clinical Assessment & Diagnosis, Employment, Consent/Declaration).

**Screen 2 — Administrative view.** Parts A/B, employer, accident logistics, consent capture. "Ready for clinician" affordance.

**Screen 3 — Clinician view.** Context summary, diagnosis grid + picker modal, clinical flags, rehabilitation, ability-to-work/certificate panel, declaration, and lodge actions.

**Screen 4 — Diagnosis picker (modal).** Terminology typeahead, code-system indicator, body site/side selectors, ACC?-flag preview, add-to-grid.

**Screen 5 — ACC18 recertification.** Post-lodgement panel to issue further certificates with new validity periods.

**Screen 5b — Add / change diagnosis (post-lodgement).** On a lodged claim, read-only diagnosis rows with status chips plus an `Add / change diagnosis` drawer: terminology picker, body site/side, read-only accident date, same-event confirmation, reason, and an "attach to ACC18" toggle. Shows the pending/decision state returned for each request. This is the primary revision flow to demonstrate — adding a new diagnosis to an already-lodged ACC45 during the initial window.

**Screen 6 — Claim list/dashboard.** Search + filter by status, date, provider; shows lodgement/decision state.

Key UI states to design: empty/new claim, in-progress with validation errors (inline red messaging like "At least one injury diagnosis is needed"), disabled-due-to-permission (Part E for non-prescribers), ready-to-lodge, lodged/read-only, and decision-returned.

---

## 10. Non-functional & compliance notes (product-level)

- **Audit trail** on every field change, consent capture, diagnosis edit, and declaration — who/when — since claims are legal records.
- **Privacy:** align consent capture and data handling with the Accident Compensation Act 2001 collection/use/disclosure basis quoted in the consent script; sensitive-claim data requires stricter access control (future).
- **Value-set versioning** recorded per claim for reproducibility.
- **Accessibility:** WCAG 2.1 AA — this is a clinical tool used under time pressure; keyboard-first diagnosis entry matters.
- **Resilience:** autosave drafts; never lose an in-progress claim.

---

## 11. Suggested build order for the Claude Code mockup

1. Claim workspace shell + claim header/status + two-pane layout.
2. Administrative form (Parts A/B + consent capture) with validation checklist.
3. Diagnosis grid + picker with a **stubbed** terminology expansion and ACC?-flag logic.
4. Clinical flags + ability-to-work/certificate panel with conditional required fields.
5. Practitioner declaration with role-gated enablement.
6. Lodgement gate + stubbed ACC response + status transitions.
7. ACC18 recertification and claim dashboard.

Start with mocked data and a fake terminology service; wire the real NZHTS `$expand`/`$validate-code` endpoints only after the interaction model is proven.

---

## Sources

- [Lodging a claim for a patient — ACC](https://www.acc.co.nz/for-providers/lodging-claims/lodging-a-claim-for-a-patient)
- [Issuing medical certificates — ACC](https://www.acc.co.nz/for-providers/treatment-recovery/issuing-medical-certificates)
- [Updating or changing a claim (add/change diagnosis) — ACC](https://www.acc.co.nz/for-providers/lodging-claims/updating-changing-claims)
- [ACC45 number change / Claim Number Allocation API — ACC](https://www.acc.co.nz/for-providers/provider-news-and-events/provider-news/acc45-number-change)
- [How to complete an ACC45 injury claim form (PDF) — ACC](https://www.acc.co.nz/assets/provider/CompleteACC45form.pdf)
- [Recovery at work – ACC work certification — RNZCUC](https://rnzcuc.org.nz/recovery-at-work-acc-work-certification/)
- [Submitting ACC18 Medical Certificates — SubmitKit](https://help.submitkit.co.nz/en/articles/9158680-submitting-acc18-medical-certificates)
- [ACC claim reference value set — NZ Health Terminology Service (FHIR)](https://nzhts.digital.health.nz/fhir/ValueSet/acc-claim-reference-set)
