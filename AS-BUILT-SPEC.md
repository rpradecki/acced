# ACC Claim Console — As-Built Replication Specification

**Purpose.** This document specifies the current build precisely enough that another
developer or AI coding platform can **replicate the exact functionality on a different
stack** (React, Vue, Svelte, Django, Rails, Flutter, etc.). It describes *what the app
does* — data, rules, states, screens, copy, and design tokens — not *how the reference
build is coded*. The reference implementation is a single-file Streamlit app
(`app.py`); nothing here depends on Streamlit except Appendix C.

**Companion documents (all in this repo).**
- `ACC-Claim-Lodgement-Product-Spec.md` — the product-level rationale and ACC domain rules.
- `ACC-FHIR-Terminology-Spec.md` — the real SNOMED/FHIR terminology binding (this app stubs it).
- `PRODUCTION-READINESS.md` — Health NZ ecosystem gap analysis. `DATABASE-SCHEMA.md` — production DDL.

**Nature of the build.** Front-end mockup. ACC lodgement, SNOMED terminology, identity, and
messaging are **stubbed** behind connectors (§13). Claim state is in-memory per session;
an in-memory **attributed, versioned claim store** (§14) backs the audit trail. No real
patient data, not for clinical use.

---

## 1. Domain in one paragraph

A New Zealand health provider lodges an **ACC45** injury claim for a patient, then may
issue **ACC18** medical certificates over time. The console splits work across an
**administrative** role (patient/accident/consent — ACC45 Parts A/B and the patient part
of E) and a **clinician** role (diagnoses, flags, work-capacity certification, and the
practitioner declaration — Parts C/D/E). A claim cannot be lodged unless it has at least
one **ACC-eligible** diagnosis (a member of the ACC claim reference set). After lodgement
the diagnosis list is read-only; new injuries from the *same accident* are added via a
**Change-in-Diagnosis** request.

---

## 2. Roles & permissions

Three first-class roles, selected by the role switcher (a dev-only stand-in for
My Health Account Workforce sign-in). Permissions come from the auth connector and are
enforced across the whole UI.

| Role key | User | Edit admin (Part A/B/consent) | Edit clinical (Part C/D/E) | Submit / lodge | View | Dashboard |
|---|---|---|---|---|---|---|
| `clerical` | R. Patel — Clerical / Reception | **Yes** | No (read-only view) | No | summary yes | shared working set |
| `clinical` | Dr A. Rangi — Clinician | Yes | **Yes** (+ sign Part E) | **Yes** | yes | shared working set |
| `audit` | M. Chen — Audit / Review | No | No | No | **all claims, read-only** | Audit dashboard |

Behaviour:
- **Clerical** edits the Administrative tab and captures consent; the Clinician tab renders as a **read-only** clinical view; the Review tab shows the summary but the **lodge control is replaced by a "cannot submit" notice**; post-lodgement diagnosis changes are hidden (clinical action).
- **Clinical** does everything, including signing Part E and lodging.
- **Audit** does not use the workspace at all. It gets its **own dashboard** listing **every** claim (all statuses/authors), **searchable by patient name or NHI**; each row has **Inspect** → a **read-only** summary plus the **attributed audit trail** (§14).

---

## 3. Information architecture & navigation

Top-level routing depends on **role** and whether a claim is open (`active_claim_id`):

- **Clerical / Clinical:** **Dashboard** (no claim open) ↔ **Workspace** (claim open; claim header bar + 3-tab nav + active panel).
- **Audit:** **Audit dashboard** (no claim open) ↔ read-only **Inspect** view (claim open). Audit never enters the editable Workspace.

**Workspace tabs** (custom button nav; active tab = filled primary style):
`📋 Administrative` · `🩺 Clinician` · `✅ Review & lodge`. Active tab stored in
`active_tab` (default `admin`).

**Dialogs (modal):**
- **Add diagnosis** — opened from the Clinician tab.
- **Add diagnosis to lodged ACC45** (Change-in-Diagnosis) — opened from the Review tab when lodged.

**Session/navigation state (in-memory):**
`claims[]`, `active_claim_id` (a.k.a. `active`), `active_tab` (`admin|clin|review`, default `admin`),
`role` (`clerical|clinical|audit`, default `clinical`), `number_seq` (int, next ACC45 number).
Plus a **process-global** attributed claim store + audit trail (§14).

---

## 4. Data model

All entities below are nested under a **Claim** (one aggregate per claim). Types are
language-neutral. Enum values are **verbatim** — reproduce exactly (they appear in the UI
and in rules).

### Claim
| Field | Type | Notes |
|---|---|---|
| `id` | string | unique |
| `reference` | string | allocated ACC45 number, e.g. `IO16457` (opaque string) |
| `number_source` | enum | `acc_allocation_api` \| `preallocated_block` |
| `created` | date | claim creation date |
| `created_by` | string | owning user (dashboard is scoped to this) |
| `lodged_on` | date\|null | set at lodgement; **anchors the 14-day repair window** (null while unsubmitted) |
| `status` | enum | `draft` \| `ready` \| `lodged` \| `accepted` \| `held` \| `declined` |
| `decision` | string\|null | ACC's cover decision: `Accepted` \| `Held` \| `Declined` \| null. **Null until ACC issues one** — lodging does not set it. ACC has no `Received` cover status; `held` is its documented under-review state. |
| `acknowledged_at` | string\|null | eLodgement transport receipt (the message reached ACC). **Not** a cover decision. |
| `encounter` | Encounter | see below |
| `patient` | Patient | Part A |
| `employment` | Employment | Part B |
| `accident` | Accident | Part B |
| `consent` | Consent | Part E (patient) |
| `diagnoses` | Diagnosis[] | Part C |
| `flags` | Flags | Part C |
| `capacity` | Capacity | Part D / ACC18 |
| `declaration` | Declaration | Part E (practitioner) |
| `change_requests` | ChangeRequest[] | post-lodgement |

### Encounter (from PAS/PMS)
`external_id` (e.g. `ENC-482173`), `source` (`pms_context`), `facility`,
`provider`, `klass` (visit class), `source_system` (e.g. `Medtech PMS`).

### Patient (Part A)
`pas_id`, `given`, `family`, `dob` (string `YYYY-MM-DD`), `nhi` (7-char, upper-cased),
`mobile`, `email`, `address`.

### Employment (Part B)
`status` (enum, see §5), `occupation`, `employer`.

### Accident (Part B)
`adate` (date\|null), `atime` (string), `location`, `scene` (enum),
`workplace` (`No`\|`Yes`), `vehicle` (`No`\|`Yes`), `sporting` (`No`\|`Yes`),
`sport` (enum, **conditional** — set only when `sporting = Yes`), `cause` (text).

### Consent (Part E patient)
`given` (bool), `at` (timestamp string\|null). `given=true` means **all three**
authorisations captured together.

### Diagnosis (Part C, 0..*)
`id`, `code` (SNOMED id), `display`, `site`, `side` (enum), `acc` (bool — ACC-eligible),
`primary` (bool), `status` (`draft`\|`lodged`\|`accepted`\|`change_pending`),
optional `source_request` (id of the ChangeRequest that created it).

### Flags (Part C)
`gradual`, `treatment`, `admitted`, `home` — each `No`\|`Yes`.

### Capacity (Part D / ACC18)
`exertion` (enum), `state` (enum), `restrictions` (text), `justification` (text),
`cert_type` (enum), `valid_from` (date\|null), `valid_to` (date\|null).

### Declaration (Part E practitioner)
`made` (bool), `date` (date\|null), `by` (string\|null), `provider_no` (string).

### ChangeRequest (post-lodgement, 0..*)
`id`, `kind` (`add`), `code`, `display`, `side`, `acc` (bool), `same_event` (bool),
`bundled` (`ACC18 medical certificate` \| `—`), `reason` (text),
`status` (`submitted`).

---

## 5. Enumerations (verbatim)

- **Employment status:** `Not employed in NZ`, `Retired`, `Employee`, `Self-employed`, `Owner employee`, `Other`.
- **Accident scene:** `Home`, `Work`, `Road`, `Sports facility`, `School`, `Other`.
- **Sport** (shown only when `sporting = Yes`): Aerobics, Athletics, Badminton, Basketball, Boating, Bowls, Boxing, Bungee Jumping, Cricket, Cycling, Dance, Diving, Equestrian, Fishing, Football (Soccer), Golf, Gymnastics, Hockey, Horse Riding, Martial Arts, Motorsport, Mountain Biking, Netball, Rowing, Rugby League, Rugby Union, Running, Sailing, Skiing, Snowboarding, Softball, Squash, Surfing, Swimming, Table Tennis, Tennis, Touch, Tramping, Trampoline, Triathlon, Volleyball, Walking, Water Polo, Weightlifting, Wrestling, Other.
- **Work exertion:** `""` (unset), `Sedentary`, `Light`, `Medium`, `Heavy`, `Very heavy`.
- **Work capacity state:** `""` (unset), `Fully fit`, `Fit for selected work`, `Fully unfit`.
- **Certificate type:** `ACC45 initial (≤14 days)`, `ACC18 (beyond 14 days)`.
- **Body side:** `Left`, `Right`, `Bilateral`, `N/A`.
- **Yes/No controls** default to `No`: accident `workplace`/`vehicle`/`sporting`; flags `gradual`/`treatment`/`admitted`/`home`.
- **Status → label** mapping: `draft`→"Draft", `ready`→"Ready to lodge", `lodged`→"Lodged", `accepted`→"Accepted", `held`→"Held", `declined`→"Declined".
- **Roles (actor):** `clerical`, `clinical`, `audit` (machine-authored audit entries also use `system`/`acc`).
- **Diagnosis status:** `draft`, `lodged`, `accepted`, `change_pending` (+ `superseded`/`declined` reserved).

---

## 6. Reference data

### 6.1 Terminology stub (the "ACC claim reference set")

The diagnosis picker searches this in-memory list. `acc=true` ⇒ member of the ACC claim
reference set ⇒ ACC-eligible. Replicate exactly (a production build swaps this for a live
SNOMED CT NZ terminology server — see the FHIR spec).

| code | display | site | acc |
|---|---|---|---|
| 283384001 | Sprain of ligament of ankle | Ankle | ✅ |
| 262911006 | Laceration of finger | Finger | ✅ |
| 20946005 | Fracture of distal radius (wrist) | Wrist | ✅ |
| 82576008 | Contusion of knee | Knee | ✅ |
| 209815008 | Sprain of rotator cuff (shoulder) | Shoulder | ✅ |
| 312608009 | Laceration - injury | | ✅ |
| 110030002 | Concussion injury of brain | Head | ✅ |
| 125605004 | Fracture of bone | | ✅ |
| 44465007 | Sprain of neck | Neck | ✅ |
| 81680005 | Closed fracture of shaft of tibia | Lower leg | ✅ |
| 7200002 | Alcohol dependence syndrome | | ❌ |
| 73211009 | Diabetes mellitus | | ❌ |
| 38341003 | Hypertensive disorder | | ❌ |
| 48694002 | Anxiety disorder | | ❌ |
| 183932001 | Presentation for social reasons | | ❌ |

Search = case-insensitive substring match on `display` **or** `code`. The picker has a
"Scope to ACC-claimable concepts" toggle (default **on**) that filters to `acc=true` only.

### 6.2 Seeded sample claims (present on first load)

**Six** claims demonstrate every dashboard state. `number_seq` starts at **16457** so new
claims never collide with the seeded references. Dates are **relative to today** (so the
demo is stable): `created`/`lodged_on` are `today − N days` as noted, driving the window
pills. Each seeded claim is also given an attributed audit history (§14) on first load.

| ref | patient | status | ages (N days ago) | pane | key data |
|---|---|---|---|---|---|
| `IO16453` | Hemi Walker (2001-05-08, NHI RTK1180) | `draft` | created 0 | Unsubmitted — **Admin step needed** | Patient from PMS; accident date/cause + consent not yet done; no diagnosis. |
| `IO16452` | Aroha Ngata (1991-06-02, NHI KLP2286) | `draft` | created 3 | Unsubmitted — **Clinician info needed** | Employee; Work accident, shoulder; consent given; dx 209815008 Right (primary). No capacity/declaration. |
| `IO16454` | David Thorne (1974-11-19, NHI MTR9043) | `ready` | created 1 | Unsubmitted — **Ready to lodge** | Self-employed builder; Home accident, ankle; dx 283384001 Left; **Fit for selected work** (restrictions); declaration made. Fully valid. |
| `IO16450` | Tomasi Vaka (1988-09-14, NHI PLR5521) | `declined` | created/lodged 12 | Submitted — **needs repair, 2 days left** | Employee courier; Road/vehicle; dx 44465007 neck; declaration made. Declined by ACC. |
| `IO16456` | Sina Faleolo (1998-02-27, NHI NBW7712) | `accepted` | created/lodged 9 | Submitted — 5 days left | Employee chef; Work accident, wrist; dx 20946005 Right (`accepted`); **Fully unfit** (justification). |
| `IO16445` | Grace Wilson (1962-01-30, NHI QDF3390) | `accepted` | created/lodged 16 | **Expired** (read-only) | Retired; Home accident, wrist; dx 20946005 Right. Past the 14-day repair window. |

Default encounter for new/seed claims: facility `Riverside Medical Centre`, provider
`Dr A. Rangi (GP)`, class `Outpatient / GP consult`, source system `Medtech PMS`,
`external_id` = `ENC-` + random 6 digits. New claims (via the button) prefill patient
**Margaret Ellery** (1949-03-11, NHI JBX4728).

---

## 7. Behaviours & business rules

### 7.1 Create claim (Dashboard → "New ACC45 claim (from PMS encounter)")
- Allocate `reference` = `"IO" + number_seq`, then `number_seq += 1`. `number_source = acc_allocation_api`.
- Simulate a PMS encounter (new `external_id`) and prefill the patient (default sample: Margaret Ellery, DOB 1949-03-11, NHI JBX4728). `status = draft`, `created = today`, `created_by = current user`, `lodged_on = null`.
- Persist an attributed "claim created" audit entry; open the claim (set `active_claim_id`), land on the Administrative tab.

### 7.2 ACC number allocation
Sequential from `number_seq`; stored as an **opaque string** (do not hard-code a format
elsewhere — see Product Spec §4.0; ACC's real format is changing). Reference is reserved
at creation; committed on lodge.

### 7.3 Consent capture (Administrative)
Before consent: show the 3-question script summary and a "Record patient consent
(all three = Yes)" button. On click: set `consent.given=true`, `consent.at = now`
(display format `DD/MM/YYYY HH:MM`). After: show a green "Consent given" banner with the timestamp.

### 7.4 Add diagnosis (Clinician → dialog)
- Search the terminology stub (§6.1); optional scope-to-eligible toggle.
- On selecting a concept, show an **eligibility banner**:
  - eligible → green: *"✓ {display} ({code}) — member of the ACC claim reference set. Supports an ACC claim."*
  - not eligible → red: *"⚠ {display} ({code}) — not in the ACC claim reference set. Can be recorded, but cannot support an ACC claim on its own. Consider a specific injury + body site."*
- Body side is **required** (`Left/Right/Bilateral/N/A`) before "Add to claim" enables.
- On add: append a Diagnosis; first diagnosis on the claim is auto-`primary=true`; `status=draft`; `acc` copied from the concept.

### 7.5 Diagnosis grid & eligibility feedback (Clinician)
- Show a live summary chip: `"{n} diagnoses · {m} ACC-eligible"`.
- Each row shows Side, an ACC? pill (`Yes` green / `Not eligible` red), and status.
- If there are diagnoses but **zero eligible**, show a red banner: *"⚠ No ACC-eligible
  diagnosis yet. Every diagnosis on this claim is outside the ACC claim reference set. Add
  at least one ACC-eligible injury to lodge — this claim cannot be submitted as-is."*
- If **no** diagnoses: red banner *"✱ At least one injury diagnosis is needed."*
- When the claim is lodged (status not `draft`/`ready`): grid is **read-only**; show a note pointing to the Review tab's post-lodgement change.
- Removal available via an "Edit diagnoses (remove)" expander while editable.

### 7.6 Clinical flags (Clinician)
Four Yes/No controls. Contextual banners when set to `Yes`:
- `treatment=Yes` → warn: *"Treatment injury — ACC2152 + patient notes required before lodgement."*
- `gradual=Yes` → warn: *"Gradual process — medical practitioner only; work history needed."*

### 7.7 Ability to work / certification (Clinician)
- `exertion` select; `state` radio (`Fully fit`/`Fit for selected work`/`Fully unfit`).
- **Conditional required fields:** `Fit for selected work` → `restrictions` required;
  `Fully unfit` → `justification` required.
- `cert_type` select (ACC45 initial vs ACC18); `valid_from`/`valid_to` dates.
- If `state` ∈ {selected work, fully unfit}: info caption about possible weekly compensation eligibility.

### 7.8 Practitioner declaration (Clinician, Part E)
- Enabled only when the role can sign Part E (**clinical**). Otherwise disable the
  provider-number field and sign button and show a warn banner: *"🔒 Part E is restricted
  to doctors and nurse practitioners. Switch to the clinical role in the sidebar to sign…"*.
- On "Complete declaration (Today)": set `made=true`, `date=today`, `by=` the signer's name
  (from auth), default `provider_no` to the HPI default (`HP-44921`) if empty; persist an
  attributed audit entry ("Part E declaration signed"). Show green confirmation.

### 7.9 Lodgement (Review tab)
- Run **validation** (§8). Show a readiness card: green "ready to lodge" or a red list of blocking errors; a warn list for non-blocking warnings.
- **Role gate:** only a role that can submit (**clinical**) sees the lodge control. Clerical instead sees a warn notice: *"Your clerical role can prepare and review this claim but cannot submit it. A clinician lodges the ACC45."*
- **"Complete & lodge ACC45"** is **disabled** unless validation passes (`can_lodge`) **and** the claim is not expired.
  On lodge: set every diagnosis `status="lodged"`, claim `status="lodged"`, `lodged_on=today` (starts the 14-day repair window), and `acknowledged_at=` the ACC connector's **transport receipt**; persist an attributed audit entry ("lodged ACC45"). `decision` stays **null** — ACC assesses cover asynchronously, and no SMS is sent yet.
- After lodge, a **Simulate ACC decision** control (Accepted/Held/Declined) sets `status`/`decision`, fires the stubbed decision SMS, and persists an attributed audit entry.

### 7.10 Post-lodgement diagnosis change (Review → dialog)
- Only when lodged. Info banner explains it's a **Change-in-Diagnosis request** (not a
  re-lodgement) and must be the **same accident**.
- Fields: terminology search + select, body side, read-only accident date, reason,
  **same-event** checkbox (required to submit), "attach to ACC18" checkbox (default on).
- If same-event unchecked: warn to lodge a new ACC45 instead; submit disabled.
- On submit: append a ChangeRequest (`kind=add`, `status=submitted`, `bundled` per toggle),
  and append a Diagnosis with `status=change_pending` linked via `source_request`; persist
  an attributed audit entry. Only the **clinical** role sees this action (clerical sees a
  "clinical action" note).

### 7.11 Role-based access & attribution
- **Clerical:** edits Administrative + consent; Clinician tab renders **read-only** (view only, banner); Review shows the summary but **no lodge** (see 7.9); post-lodgement changes hidden.
- **Clinical:** full edit + sign Part E + lodge + post-lodgement changes.
- **Audit:** no Workspace; uses the Audit dashboard + Inspect (9.7 / 9.8).
- **Attribution:** every meaningful action — *claim created, consent recorded, diagnosis added/removed, Part E signed, lodged, ACC decision, diagnosis-change request* — persists an attributed, versioned save (author name + role) to the store, feeding the audit trail (§14).

---

## 8. Validation rules & lodge gate

`validate(claim)` returns **errors** (block lodge), **warnings** (non-blocking), and
`can_lodge = (errors is empty)`. Messages are **verbatim** (shown in the readiness list).

**Errors (block lodging):**
1. `Patient name is required.` — if `given` or `family` empty.
2. `Date of birth is required.` — if `dob` empty.
3. `Accident date is required.` — if `accident.adate` empty.
4. `Cause of injury is required.` — if `accident.cause` blank.
4a. `Select the sport for the sporting injury.` — if `accident.sporting = Yes` and no `sport` chosen.
5. `Patient consent (all three authorisations) must be recorded.` — if `consent.given` false.
6. `At least one injury diagnosis is needed.` — if no diagnoses.
7. `At least one ACC-eligible diagnosis is required to lodge.` — if diagnoses exist but none has `acc=true`. **(the hard eligibility gate)**
8. `Diagnosis "{display}" needs a body side (or N/A).` — per diagnosis lacking `side`.
9. `Fit for selected work requires restrictions/activities.` — if capacity state = selected work and `restrictions` blank.
10. `Fully unfit requires a justification.` — if capacity state = fully unfit and `justification` blank.
11. `Practitioner declaration (Part E) must be completed by an eligible signer.` — if `declaration.made` false.
12. `Provider number is required.` — if `declaration.provider_no` empty.

**Warnings (do not block):**
- `No NHI supplied — slows processing.` — if `nhi` empty.
- `No mobile — patient won't get an SMS decision.` — if `mobile` empty.
- `Accident was over 12 months ago — delayed lodgement needs supporting clinical records.` — if the accident is ≥ 365 days ago.

The lodge control must be **disabled** while any error exists; in a real build, re-validate
server-side at lodge so a stale client cannot bypass the gate.

---

## 9. Screen specifications

### 9.1 Dashboard — "ACC submissions" (clerical & clinical; two panes + expired)
The clerical/clinical dashboard shows the **shared practice working set** (all claims —
not per-user), organised around the **14-day post-lodgement repair window**
(`EDIT_WINDOW_DAYS = 14`, `LODGE_LIMIT_DAYS = 365`).

- Brand header bar with the signed-in user + role.
- Heading **"ACC submissions"** with a note: unsubmitted referrals have no edit clock but should be lodged within **12 months** of the accident; once **submitted**, editable for **14 days** for update/revision/repair, then read-only.
- **Summary metric strip:** Unsubmitted · Ready to lodge · Submitted (14-day) · Needs repair (red when >0) · Expiring ≤3 days (amber when >0).
- Primary button **"➕ New ACC45 claim (from PMS encounter)"**.

Two panes for the active working set (`days_left > 0`), each sorted most-urgent-first, sharing columns `ACC45 no.` (mono), `Patient`, `Status`, `Accident`, **`Edit window`**, action button:

- **Pane 1 — Unsubmitted** (status `draft` or `ready`). **Unsubmitted claims have no edit clock** — the last column (**"LODGE BY"**) shows *lodgement timeliness* relative to the accident, not a repair countdown: "N days since accident" (muted), "Approaching 12-month limit" (amber ≥ ~300 days), or "Delayed lodgement >12mo — extra records" (red ≥ 365 days). The **Status** column shows the *next step to lodge*, from `readiness(claim)`:
  - **"Admin step needed"** (amber) — a clerical/administrative field is outstanding: patient name/DOB, accident date, cause, consent, or sport (when sporting). *Takes priority.*
  - **"Clinician info needed"** (blue) — admin done, but clinical items outstanding: ≥1 (ACC-eligible) diagnosis, body side, conditional capacity text, declaration, or provider number.
  - **"Ready to lodge"** (green) — validation passes.
  Row action = **Open** → lands on the **Administrative** tab.
- **Pane 2 — Submitted** (status `lodged` / `accepted` / `held` / `declined`, still inside the 14-day window). Last column (**"REPAIR WINDOW"**) shows the post-lodgement countdown. The **Status** column shows the ACC status pill + decision; `held`/`declined` get a "needs action" pill. Row action = **Open** → lands on the **Review & lodge** tab.

- **Expired** (`days_left ≤ 0`) in a collapsed, read-only expander; rows open in **View** (read-only) mode.

**Window rules.**
- The 14-day window is **post-lodgement**: `days_left = 14 − (today − lodged_on).days`; **`None` for unsubmitted** (no `lodged_on`). `is_expired = days_left is not None and ≤ 0`. `lodged_on` is set when the claim is lodged.
- **Repair-window pill (Submitted only):** neutral/blue normally; **amber ≤ 7**; **red ≤ 3**; "Repair window expired" at ≤ 0. Nothing shown for unsubmitted.
- When expired, the claim is **read-only**: workspace read-only banner, clinician grid locked, lodging disabled. (Ongoing certification continues via a new ACC18, out of this window.)
- **Lodgement timeliness (separate rule):** ACC considers claims lodged **within ~12 months** of the accident (`LODGE_LIMIT_DAYS = 365`); ≥ 12 months adds a non-blocking warning ("delayed lodgement needs supporting clinical records"; sensitive claims excepted).

### 9.2 Workspace header + tab nav
- "← Home" button (clears `active_claim_id`).
- Header bar: "Health NZ" + `reference` chip + status pill + patient/encounter/accident-date subtext + a live "✓ ready" / "{n} to fix" indicator.
- Tab bar (bordered): three buttons; active = primary (blue fill, white text), others = secondary (white, blue text). Clicking sets `active_tab` and re-renders the panel.

### 9.3 Administrative tab
Cards, in order: **Encounter context** (chips: encounter, source system, facility,
provider, ACC45 no. + allocation source; note "identity inherited — verify, don't
re-key"); **Patient · Part A**; **Employment · Part B** (occupation disabled when "Not
employed in NZ"; employer disabled unless "Employee"); **Patient consent · Part E**;
**Accident · Part B** (3-col date/time/location; scene + three Yes/No; a **Sport** dropdown
that appears only when *Sporting injury? = Yes* — required in that case; cause textarea).

### 9.4 Clinician tab
Cards: **Context** (chip strip of patient/accident/scene/consent + cause); **Injury
diagnosis & assistance · Part C** (summary chip, Add button or lodged read-only note,
diagnosis table, eligibility banners, remove expander); **Clinical flags**; **Ability to
work · Part D / ACC18**; **Practitioner declaration · Part E** (role-gated). For the
**clerical** role the whole tab renders **read-only** (a compact view of Parts C/D/E) with
a "Clinical section — read-only" banner; editing is clinical-only.

### 9.5 Review & lodge tab (in this order)
1. **Lodgement readiness** card (errors/warnings; lodge button when draft/ready **and** the role can submit — clerical sees a "cannot submit" notice instead).
2. **Full ACC45 summary** (§10) — appears directly under readiness, for every state.
3. **Post-lodgement** card — only when lodged: lodged banner + decision, Simulate ACC
   decision buttons (while `lodged`), the "Add / change diagnosis (post-lodgement)" action
   (**clinical** only; clerical sees a note), and a change-requests table.

### 9.6 Dialogs
- **Add diagnosis:** scope toggle, search, result select, eligibility banner, body-side radio, "Add to claim".
- **Add diagnosis to lodged ACC45:** info banner, search/select, body-side, read-only accident date, reason, same-event checkbox (required), attach-to-ACC18 checkbox, "Submit change request".

### 9.7 Audit dashboard (audit role)
- Brand header (Audit / Review) + heading **"Audit · all ACC submissions"**.
- **Search box** — filters all claims by patient name **or** NHI (case-insensitive substring).
- Table of **every** claim (all statuses/authors): `ACC45 no.`, `Patient`, `NHI`, `Status`, `Created by`, and an **Inspect** button per row → opens the Inspect view.

### 9.8 Inspect view (audit role, read-only)
- "← Back to audit" button; header with reference, status, patient, NHI, created-by, and a "read-only" tag.
- The **full ACC45 summary** (§10), read-only.
- **Audit trail** card — "Audit trail · attributed change history" table: `Ver | When | Author | Role | Action`, oldest-first (from the store's `versions(reference)`; see §14).

---

## 10. Full ACC45 summary (Review tab)

A read-only rendering of everything entered, as a labelled definition grid + tables.
Sections and fields, in order:

1. **Claim summary · ACC45** — ACC45 number, Status (label), Encounter, Source system, Facility, Attending provider.
2. **Patient · Part A** — Name, Date of birth, NHI, Mobile, Email, Address.
3. **Employment · Part B** — Employment status, Occupation, Employer.
4. **Accident · Part B** — Date/time, Location, Scene, Workplace accident, Moving vehicle on road, Sporting injury, then **Cause of injury** (full width).
5. **Consent · Part E (patient)** — "Consent recorded" pill + timestamp, or "Consent not recorded".
6. **Diagnoses · Part C** — the diagnosis table (Diagnosis+code, Side, ACC?, Status), then a chip strip of the four flags.
7. **Ability to work · Part D / ACC18** — Normal work exertion, Work capacity, Certificate, Valid range, then **Restrictions/justification** (full width) if present.
8. **Practitioner declaration · Part E** — "Declaration made" pill + date/signer/provider, or "Declaration not completed".

Any empty value renders as `—` so gaps are obvious before lodging.

---

## 11. Visual design system (Health New Zealand | Te Whatu Ora)

Reproduce these tokens to match the look on any stack. Source: Te Whatu Ora digital
identity brand guidelines.

**Palette**
| Token | Hex | Use |
|---|---|---|
| navy | `#252A47` | header/sidebar background, headings |
| deep blue (primary) | `#002E6E` | primary buttons, active tab, section labels, accents |
| mid blue (focus) | `#7EB6DC` | focus rings |
| light blue | `#EEF4FA` | tab track, secondary background, info banners |
| teal / teal-light | `#A7DEE1` / `#D3EFF0` | accents |
| success | bg `#E7F4EC` · fg `#17663E` · border `#B7E0C7` | ok pills/banners |
| warning | bg `#FFF6E5` · fg `#8A5A00` · border `#F6DCA1` | warn |
| error | bg `#FBEBEA` · fg `#8F2A22` · border `#F3C3BF` | error/blocked |
| neutrals (navy-tinted) | `#F4F8FC`,`#EDF2F8`,`#D8E3EF`,`#C3D2E2`,`#8398B0`,`#566579`,`#3E4C60`,`#2B3850`,`#252A47`,`#1A1F36` | text, borders, backgrounds |

**Typography:** Fira Sans (400/500/600/700), Google Fonts. Base size ~13px; compact, dense.

**Components**
- **Card:** white, 1px `#D8E3EF` border, 12px radius, subtle shadow.
- **Section label (`sec`):** 11px, uppercase, letter-spaced, deep-blue, bold.
- **Pill:** rounded 999px, 10.5px bold; variants ok/err/warn/blue + neutral.
- **Banner:** 9px radius, tinted bg + matching border, per semantic colour.
- **KV chip:** slate-50 bg, 1px border, small; label muted, value navy-bold.
- **Table:** uppercase muted header on slate-50, 1px row separators.
- **Tab bar:** light-blue track container; active tab = deep-blue fill + white text; inactive = white + deep-blue text (both must stay readable).
- **Buttons:** primary = deep-blue fill/white; secondary = white/deep-blue; 8px radius; mid-blue focus ring.
- **Sidebar:** navy background, light text.
- **Density:** tight vertical spacing; content clears the top app chrome (≈4rem top offset in the reference build).

---

## 12. Acceptance criteria (parity tests)

A replicated build should pass all of these (mirrors the reference test suite):

1. **Seed load:** six claims appear — `IO16453` + `IO16452` (draft/unsubmitted), `IO16454` (ready), `IO16450` (declined), `IO16456` (accepted), `IO16445` (accepted, expired). Unsubmitted split by readiness (Admin step / Clinician info / Ready to lodge).
2. **Create:** "New claim" allocates the next `IO#####`, opens the workspace on the Administrative tab.
3. **Tabs:** three visible, readable tabs; clicking switches the panel; the active tab is visually distinct and legible.
4. **Eligibility gate — block:** a claim whose only diagnosis is non-eligible (e.g. `183932001` Presentation for social reasons) is **not lodgeable**; the readiness list contains "At least one ACC-eligible diagnosis is required to lodge." and the lodge button is disabled.
5. **Eligibility gate — pass:** adding one `acc=true` diagnosis (with all other required fields) enables lodging.
6. **Lodge:** lodging flips status to `lodged`, records `acknowledged_at` (the transport receipt) while leaving `decision` null, marks diagnoses `lodged`, and reveals the post-lodgement change action.
7. **Read-only after lodge:** the Clinician diagnosis grid is read-only once lodged.
8. **Post-lodgement change:** requires same-event; on submit, creates a ChangeRequest and a `change_pending` diagnosis row.
9. **Part E signer gate:** the Part E declaration can be signed only by the **clinical** role; for clerical/audit the sign control is disabled with an explanatory banner.
10. **Review summary:** the Review tab shows the full ACC45 summary (all Part A–E sections with entered values) directly under Lodgement readiness, in every claim state.
11. **Layout:** the app header and controls are not obscured by the top chrome.
12. **14-day window:** submitted referrals show a post-lodgement repair countdown; ≤3 days from expiry shows a red pill and counts in "Expiring ≤3 days"; past 14 days a referral is read-only in the Expired section. Unsubmitted referrals show 12-month lodgement timeliness, not an edit clock.
13. **Roles:** `clerical` edits Administrative but sees the Clinician tab read-only and cannot lodge (a "cannot submit" notice replaces the lodge control); `clinical` edits everything, signs Part E, and can lodge; `audit` gets an all-claims dashboard searchable by name/NHI and read-only Inspect.
14. **Attributed audit trail:** every save is versioned and attributed; the Audit → Inspect view shows the change history with author + role per version (e.g. R. Patel/clerical then Dr A. Rangi/clinical), and the same claim's summary read-only.

---

## 13. External integration seams (connectors)

Every boundary to an external system is isolated behind a **connector** (`connectors.py`)
with a documented **stub**. A replica should keep the same seam boundaries so real HNZ
services can be dropped in without touching UI/logic. Connectors and the operations the
app calls:

| Connector | App calls | Real HNZ service / standard | Status |
|---|---|---|---|
| `auth` | `current_user(role)`, `can_sign_part_e(role)` | My Health Account Workforce (OIDC) | stub |
| `nhi` | `validate(nhi)`, `lookup(nhi)` | NHI FHIR API (Digital Services Hub); HISO 10046 | stub |
| `hpi` | `default_provider_number()`, `provider_lookup()` | HPI FHIR API (Digital Services Hub); HISO 10005/6 | stub |
| `pms` | `get_encounter_context()` | PMS/PAS via SMART on FHIR launch | stub |
| `sdhr` | `get_core_health_info(nhi)`, `contribute(claim)` | Shared Digital Health Record (SDHR) FHIR API — replaces Hira | stub |
| `terminology` | `search(q, eligible_only)`, `is_acc_eligible(code)` | SNOMED CT NZ Edition (`$expand`/`$validate-code`) | stub |
| `acc` | `allocate_claim_number(seq)`, `lodge(claim)`, `decision(choice)` | ACC Claim Number Allocation API + eLodgement | stub |
| `audit` | `record(author, role, action, reference, detail)`, `history(reference)` | append-only audit (FHIR AuditEvent) | stub |
| `persistence` | `save(claim, author, role, action)`, `versions(reference)`, `load_all()` | NZ-region datastore (see §14) | stub |
| `notification` | `send_decision_sms(...)` | messaging provider | stub |

Full gap analysis, standards, and go-live gate: **`PRODUCTION-READINESS.md`**. A replica
is *mockup-conformant* if it satisfies §§2–12 with stubs; *production-conformant* only when
the P0 connectors/standards in that document are met.

---

## 14. Claim store & audit trail (attributed persistence)

The claim datastore is modelled behind the **`persistence`** connector, built around the
claim aggregate in §4. **Every save is versioned and attributed to its author**, and
mirrored into the **`audit`** trail; the Audit **Inspect** view renders that trail.

**Store schema (target).**
```
claim(reference PK, status, created, created_by, lodged_on, decision,
      patient/employment/accident/consent/capacity/declaration/flags …)
diagnosis(id, claim_ref FK, code, system, display, side, acc_eligible, status)
change_request(id, claim_ref FK, kind, code, same_event, bundled, status)
claim_version(reference FK, version, ts, author, role, action)   -- append-only, one row per save
audit_event(ts, author, role, action, reference, detail)         -- who/what/when/why
```

**Save/attribution rule.** `persistence.save(claim, author, role, action)` appends a
`claim_version` (auto-incrementing `version`, timestamp, author name, role, action label),
snapshots the claim, and writes an `audit_event`. The app calls it on every meaningful,
author-attributable action: **claim created, consent recorded, diagnosis added/removed,
Part E declaration signed, lodged, ACC decision, diagnosis-change request**. So each entry
names the person and role responsible.

**Audit-trail visibility.** The Audit role's **Inspect** view shows the read-only ACC45
summary **plus** an "Audit trail · attributed change history" table:
`Ver | When | Author | Role | Action` — oldest-first, e.g.:

| Ver | When | Author | Role | Action |
|---|---|---|---|---|
| v1 | … | R. Patel | clerical | claim created |
| v2 | … | R. Patel | clerical | patient details & consent recorded |
| v3 | … | Dr A. Rangi | clinical | diagnoses & clinical assessment added |
| v4 | … | Dr A. Rangi | clinical | Part E declaration signed |
| v5 | … | Dr A. Rangi | clinical | lodged ACC45 |
| v6 | … | ACC (system) | acc | ACC decision: Accepted |

**Production notes.** Make `claim_version`/`audit_event` **append-only/immutable**, record
reads of patient data too, and retain per records-management policy (see PRODUCTION-READINESS
§G/§H). The store is process-global in the stub; a real build is a concurrency-safe DB in an
approved NZ region with optimistic locking.

**Full schema:** a production-oriented PostgreSQL schema (DDL, ERD, indexes, immutability,
privacy/residency, and the mapping back to the app model) is in **`DATABASE-SCHEMA.md`**.

---

## Appendix A — State transitions

```
draft ──(validate passes + lodge)──► lodged ──(simulate)──► accepted | held | declined
ready ──(lodge)──────────────────► lodged
(seed claims may start directly in ready or accepted)
```
Diagnosis.status: `draft` → (lodge) `lodged`; post-lodgement additions enter as
`change_pending`; seeded lodged diagnoses may be `accepted`.

## Appendix B — Exact UI copy index
The verbatim strings a replica must reproduce live in: §7 (banners), §8 (validation
messages), §9 (labels), §10 (summary section titles). Treat them as fixed content.

## Appendix C — Reference implementation (non-normative)
**Streamlit** app: `app.py` (UI + logic) + `connectors.py` (external seams §13, incl. the
attributed store §14). State in `st.session_state`; tabs built from buttons (not `st.tabs`)
for reliability; dialogs via `st.dialog`; a Tailwind-style CSS layer injected via
`st.markdown` carrying the tokens in §11. Deploys on Streamlit Community Cloud from GitHub
(`requirements.txt`: `streamlit>=1.37`). Companion docs in the repo: `PRODUCTION-READINESS.md`
(gap analysis), `DATABASE-SCHEMA.md` (production DDL). None of this is required to replicate —
any stack that satisfies §§2–14 is conformant.
