# ACC Claim Console — Production Readiness & Gap Analysis

**Context.** The current build is a functional **mockup**. To deploy into the Health New
Zealand | Te Whatu Ora digital ecosystem it must integrate with national services and
meet health-sector standards. This document enumerates the gaps, maps each to the real
HNZ service/standard, and points to the **connector stub** that already marks the
integration seam in code (`connectors.py`). Every external boundary is stubbed today and
listed in the app sidebar under *Integration status*.

**How the stubs work.** `connectors.py` exposes one object per external system
(`auth`, `nhi`, `hpi`, `pms`, `terminology`, `acc`, `audit`, `persistence`,
`notification`). Each reproduces the mockup's behaviour and documents the real service.
`CONNECTOR_MODE` flags each as `stub`. Going live = implementing the real client inside
the connector; `app.py` should not need to change.

Severity: **P0** = blocks any real deployment · **P1** = required for production ·
**P2** = required for scale/quality.

---

## A. Identity & authorisation (P0) — *connector: `auth`*
**Gap.** No real authentication or authorisation. The role switcher is a dev-only simulator.
**Target.** **My Health Account Workforce** (OIDC/OAuth2) for clinician/admin sign-in;
map workforce identity → app roles/scopes; enforce MFA, session timeout, and per-action
authorisation **server-side**. RealMe / My Health Account for any consumer-facing flow.
**Also needed.** Remove the role switcher; least-privilege RBAC (admin vs prescriber vs
limited scope); scope-of-practice checks for who may lodge which claim types.
**Record-level visibility.** The prototype assumes a **single practice/facility** and does
**not** scope by facility; within that one practice it demonstrates a per-identity **working
set** — claims a user created or opened — split from a pool of the rest of the practice's
claims they can pull from. Production is **multi-facility** and must add facility scoping as
a **server-side** boundary — **row-level security keyed on the facility (HPI Organisation)**,
not a UI filter — so a user sees only their own facility's claims, with **break-glass**
access (an explicit reason captured to the audit trail, flagged for review) for
cross-facility or **sensitive-claim** access. The per-identity "touched" set is a
convenience view, not a security control — visibility must be governed by facility + role.

## B. Patient identity & demographics (P0) — *connector: `nhi`*
**Gap.** NHI is a regex format check; no lookup; demographics are typed/seeded.
**Target.** **NHI FHIR API** (Health NZ **Digital Services Hub**), master source of patient
identity. Real **HISO 10046** check-character validation; JIT demographic retrieval;
reconcile the PMS patient to a verified NHI. Never cache beyond the consented purpose.

## C. Provider & facility identity (P1) — *connector: `hpi`*
**Gap.** Provider number is free text defaulting to a sample; no verification.
**Target.** **HPI FHIR API** (Digital Services Hub) — Practitioner (CPN), Organisation,
Facility. Resolve the signed-in identity to HPI, confirm registration status/scope, and
populate the provider number and facility from HPI (HISO 10005/10006).

## D. Encounter / launch context (P1) — *connector: `pms`*
**Gap.** The encounter and patient are simulated on "New claim".
**Target.** **SMART on FHIR EHR launch** from the PMS/PAS (Medtech, Indici, Profile, …);
inherit the FHIR Encounter + Patient; no re-keying. Support standalone launch as a fallback.

## D2. Shared health record (P1) — *connector: `sdhr`*
**Gap.** No integration with the national shared record.
**Target.** **Shared Digital Health Record (SDHR)** — Health NZ's national shared record
(supersedes the earlier **Hira** programme). With patient consent, read core health info
to contextualise the claim and contribute the lodged encounter/diagnoses to the shared
record via the **SDHR FHIR API** (fhir-ig.digital.health.nz/sdhr). Honour SDHR consent and
access controls. (Programme phasing in; general API availability is staged.)

## E. Clinical terminology (P1) — *connector: `terminology`*
**Gap.** 15-concept in-memory sample of the ACC claim reference set; no live validation.
**Target.** **SNOMED CT NZ Edition** terminology server (NZHTS / Ontoserver) via FHIR
`ValueSet/$expand` (typeahead) and `$validate-code` (the ACC? flag), bound to
`acc-claim-reference-set`. Pin & record the value-set version at lodgement. Support
Read/ICD-10 maps for interop. (Full detail: `ACC-FHIR-Terminology-Spec.md`.)

## F. ACC lodgement & numbering (P0) — *connector: `acc`*
**Gap.** Claim numbers are a local sequence; "lodge" returns a canned acknowledgement;
decisions are simulated by buttons.
**Target.** ACC **Claim Number Allocation API** (on-demand ACC45 numbers) and ACC
**eLodgement** for ACC45/ACC18 (HealthLink/PMS messaging and/or API). Persist ACC
acknowledgements; receive **asynchronous cover decisions** (webhook/poll). Handle
ACC2152 (treatment injury) and the supplementary flows (ACC1). Keep the ACC45 number an
opaque string (format is changing).

## G. Persistence & data residency (P0) — *connector: `persistence`*
**Gap.** All state is in-session memory; nothing persists; single-user.
**Target.** A durable datastore hosted in an **approved NZ region** (data
sovereignty), encryption at rest, backups/retention, concurrency-safe multi-user access,
optimistic locking, and **claim versioning/amendment history**. Consider Māori Data
Sovereignty (Te Mana Raraunga) principles.
**Concurrency (not in the prototype).** The prototype edits a single shared in-memory claim
object, so there is no cross-user contention to resolve; claims are **shared-editable** by
any authorised same-facility user. Production is multi-user and must add **optimistic
locking**: each open records the `claim_version` it loaded, and a save is **rejected if
another author has saved since** — prompting the editor to reload and re-apply their change
rather than silently clobbering the other author's edit. (Lodged claims are already
edit-locked except via post-lodgement change requests, so contention is mainly on drafts.)
**Retention policy.** The app keeps ACC45 referrals editable for a **14-day
update/revision/repair window** (`EDIT_WINDOW_DAYS`), after which they become read-only
and drop off the user's active dashboard. The datastore must enforce this policy (and any
longer statutory retention for the record itself) rather than relying on in-session state.

## H. Audit trail (P0) — *connector: `audit` + `persistence`*
**Gap.** Audit is an in-memory list lost on restart.
**Demonstrated in the stub.** The `persistence` store now versions and **attributes every
save to its author (name + role)** and mirrors it into the `audit` trail; the Audit role's
**Inspect** view renders the per-claim change history (`Ver | When | Author | Role |
Action`). See AS-BUILT-SPEC §14 for the store schema (`claim`, `diagnosis`,
`change_request`, `claim_version`, `audit_event`).
**Target.** Make it tamper-evident and **append-only/immutable**, audit **every read** of
patient data too (not just writes), independently reviewable, retained per records policy.
FHIR `AuditEvent` is a natural fit.

## I. Privacy & consent (P0)
**Gap.** Consent is captured as a boolean + timestamp; no access transparency.
**Target.** Compliance with the **Privacy Act 2020** and **Health Information Privacy Code
2020**: auditable consent aligned to the ACC/Accident Compensation Act 2001 basis, patient
access/transparency, breach processes, and role-scoped access to sensitive claims.

## J. Security (P0)
**Gap.** No secrets management, transport hardening, threat model, or pen-testing.
**Target.** TLS everywhere; secrets in a managed vault; **NZISM** / ISO 27001 alignment;
threat model + security review; dependency scanning; rate limiting; input validation;
CSRF/session protections. Security assurance before go-live.

## K. Clinical safety (P1)
**Gap.** No clinical risk management artefacts.
**Target.** A clinical safety case with hazard log and clinical risk management (per
NZ health clinical-safety expectations, e.g. equivalent to DCB0129/0160), signed off by a
named clinical safety officer.

## L. Interoperability & conformance (P1)
**Gap.** Data model is app-internal; no FHIR conformance.
**Target.** Model Patient/Practitioner/Encounter/Organization on the **NZ Base FHIR IG
v3.0.1** (HISO 10083), register any published artefacts in the **NZ FHIR Registry**, and
expose/consume FHIR APIs conformantly.

## M. Accessibility (P1)
**Gap.** Not audited; custom CSS not verified for contrast/keyboard/screen-reader.
**Target.** **NZ Government Web Accessibility Standard 1.1** + **WCAG 2.1 AA**: colour
contrast, full keyboard operation, focus order, labels/ARIA, screen-reader testing.

## N. Te Ao Māori, te reo & equity (P1)
**Gap.** English-only; no bilingual or equity considerations.
**Target.** Bilingual (te reo Māori) UI where appropriate, correct macrons, culturally
safe language, and equity of access in line with Health NZ expectations.

## O. Observability & operations (P2)
**Gap.** No logging/metrics/alerting, environments, CI/CD, or DR.
**Target.** Structured logging, metrics, alerting; dev/test/prod environments with config
management; CI/CD with automated tests + security scan; backup/restore and disaster
recovery; defined SLAs/support.

## P. Notifications (P2) — *connector: `notification`*
**Gap.** No outbound messaging.
**Target.** Templated, auditable SMS/email (e.g. ACC cover-decision SMS to the patient),
respecting contact consent/preferences.

## Q. Testing & assurance (P1)
**Gap.** Smoke/parity tests only.
**Target.** Unit/integration/e2e coverage, contract tests against each connector, security
review, accessibility audit, clinical validation, and provider UAT.

---

## Connector ↔ gap map

| Connector (`connectors.py`) | Real HNZ service / standard | Gaps |
|---|---|---|
| `auth` | My Health Account Workforce (OIDC) | A |
| `nhi` | NHI FHIR API (Digital Services Hub); HISO 10046 | B |
| `hpi` | HPI FHIR API (Digital Services Hub); HISO 10005/6 | C |
| `pms` | PMS/PAS via SMART on FHIR launch | D |
| `sdhr` | Shared Digital Health Record (SDHR) FHIR API — replaces Hira | D2 |
| `terminology` | SNOMED CT NZ Edition (NZHTS/Ontoserver) | E |
| `acc` | ACC Claim Number Allocation API + eLodgement | F |
| `persistence` | NZ-region datastore; data sovereignty | G |
| `audit` | Append-only audit (FHIR AuditEvent) | H |
| `notification` | Messaging provider | P |
| *(cross-cutting, no single connector)* | Privacy Act 2020 / HIPC 2020, NZISM, clinical safety, NZ Base FHIR IG, WCAG/NZ a11y, te reo, ops | I, J, K, L, M, N, O, Q |

## Go-live gate (minimum)
P0 items — **A, B, F, G, H, I, J** — must be delivered and assured before any real
patient/claim data flows. The stubs make each of these an explicit, isolated unit of work.

---

## Sources
- [Information for IT vendors and developers — Health NZ (NHI/HPI APIs)](https://www.tewhatuora.govt.nz/health-services-and-programmes/health-identity/information-for-it-vendors-and-developers)
- [Digital Services Hub — NHI FHIR API](https://www.tewhatuora.govt.nz/health-services-and-programmes/digital-health/digital-services-hub/explore-apis-digital-services/national-health-index-fhir-api)
- [Digital Services Hub — HPI FHIR API](https://www.tewhatuora.govt.nz/health-services-and-programmes/digital-health/digital-services-hub/explore-apis-digital-services/health-provider-index-api)
- [Shared Digital Health Record (SDHR) — Health NZ](https://www.tewhatuora.govt.nz/health-services-and-programmes/digital-health/shared-digital-health-record)
- [NZ SDHR FHIR API / Implementation Guide](https://fhir-ig.digital.health.nz/sdhr/index.html)
- [New Zealand FHIR Registry / NZ Base IG — Health NZ](https://health.govt.nz/our-work/digital-health/digital-health-sector-architecture-standards-and-governance/health-information-standards-0/new-zealand-fhir-registry)
- [My Health Account Workforce brand & integration (PDF) — Te Whatu Ora](https://www.tewhatuora.govt.nz/assets/Health-services-and-programmes/Digital-health/Digital-health-identity/Brand-guidelines-My-Health-Account-Workforce-V3.pdf)
