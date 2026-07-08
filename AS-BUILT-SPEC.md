# ACC Claim Console — As-Built Replication Specification

**Purpose.** This document specifies the current build precisely enough that another
developer or AI coding platform can **replicate the exact functionality on a different
stack** (React, Vue, Svelte, Django, Rails, Flutter, etc.). It describes *what the app
does* — data, rules, states, screens, copy, and design tokens — not *how the reference
build is coded*. The reference implementation is a single-file Streamlit app
(`app.py`); nothing here depends on Streamlit except Appendix C.

**Companion documents.**
- `../ACC-Claim-Lodgement-Product-Spec.md` — the product-level rationale and ACC domain rules.
- `../ACC-FHIR-Terminology-Spec.md` — the real SNOMED/FHIR terminology binding (this app stubs it).

**Nature of the build.** Front-end mockup. ACC lodgement and SNOMED terminology are
**stubbed**; all state is **in-memory per session** (no database, no network). No real
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

A single **role switcher** (global) selects the active user. Role affects only the
practitioner declaration and is enforced in the declaration UI.

| Role key | Display label | Can complete Part E declaration? |
|---|---|---|
| `prescriber` | Dr A. Rangi — GP (prescriber) | **Yes** |
| `limited` | J. Neho — Physiotherapist (limited) | No (control disabled, reason shown) |
| `admin` | R. Patel — Reception (admin) | No |

> Only `prescriber` may sign Part E and enter the provider number. Other roles see the
> declaration controls disabled with an explanatory banner. (All roles can otherwise
> view/edit the form in this mockup; a production build would scope Admin vs Clinician
> tabs per role — see Product Spec §2.)

---

## 3. Information architecture & navigation

Two top-level views, switched by an in-memory `active_claim_id`:

1. **Dashboard** (`active_claim_id` is null) — brand header, "New claim" action, and a
   table of claims.
2. **Workspace** (a claim is open) — claim header bar, a **3-tab nav**, and the active tab's panel.

**Workspace tabs** (custom button nav; active tab = filled primary style):
`📋 Administrative` · `🩺 Clinician` · `✅ Review & lodge`. Active tab stored in
`active_tab` (default `admin`).

**Dialogs (modal):**
- **Add diagnosis** — opened from the Clinician tab.
- **Add diagnosis to lodged ACC45** (Change-in-Diagnosis) — opened from the Review tab when lodged.

**Session/navigation state (in-memory):**
`claims[]`, `active_claim_id`, `active_tab` (`admin|clin|review`), `role`
(`prescriber|limited|admin`), `number_seq` (int, next ACC45 number).

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
| `created` | date | claim creation date — anchors the 14-day edit window |
| `created_by` | string | owning user (dashboard is scoped to this) |
| `status` | enum | `draft` \| `ready` \| `lodged` \| `accepted` \| `held` \| `declined` |
| `decision` | string\|null | `Received` \| `Accepted` \| `Held` \| `Declined` \| null |
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

Three editable claims demonstrate each state. `number_seq` starts at **16457** so new
claims never collide with the seeded references.

| ref | patient | status | key data |
|---|---|---|---|
| `IO16452` | Aroha Ngata (1991-06-02, NHI KLP2286) | `draft` | Employee, warehouse; Work accident 2026-07-06 14:20, "lifting a box off a pallet – felt sudden shoulder pain"; consent given; dx 209815008 Right (primary). No certification/declaration yet. |
| `IO16454` | David Thorne (1974-11-19, NHI MTR9043) | `ready` | Self-employed builder; Home accident 2026-07-07 09:05, "slipped off a step ladder – landed awkwardly on left ankle"; consent given; dx 283384001 Left; capacity **Fit for selected work** (restrictions text), ACC18 valid 2026-07-07→21; declaration made (HP-44921). Fully valid → lodgeable. |
| `IO16456` | Sina Faleolo (1998-02-27, NHI NBW7712) | `accepted` | Employee chef; Work accident 2026-06-30 19:45, "slipped on wet kitchen floor – put out right hand to break the fall"; consent given; dx 20946005 Right (status `accepted`); capacity **Fully unfit** (justification), ACC18 valid 2026-06-30→07-28; declaration made. Lodged & accepted. |

Default encounter for new/seed claims: facility `Riverside Medical Centre`, provider
`Dr A. Rangi (GP)`, class `Outpatient / GP consult`, source system `Medtech PMS`,
`external_id` = `ENC-` + random 6 digits.

---

## 7. Behaviours & business rules

### 7.1 Create claim (Dashboard → "New ACC45 claim (from PMS encounter)")
- Allocate `reference` = `"IO" + number_seq`, then `number_seq += 1`. `number_source = acc_allocation_api`.
- Simulate a PMS encounter (new `external_id`) and prefill the patient (default sample: Margaret Ellery, DOB 1949-03-11, NHI JBX4728). `status = draft`.
- Open the claim (set `active_claim_id`), land on the Administrative tab.

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
- If role ≠ `prescriber`: disable the provider-number field and the sign button; show a
  warn banner: *"🔒 Part E is restricted to doctors and nurse practitioners…"*.
- On "Complete declaration (Today)": set `made=true`, `date=today`, `by="Dr A. Rangi"`,
  and default `provider_no` to `HP-44921` if empty. Show green confirmation with date/signer.

### 7.9 Lodgement (Review tab)
- Run **validation** (§8). Show a readiness card: green "ready to lodge" or a red list of blocking errors; a warn list for non-blocking warnings.
- **"Complete & lodge ACC45"** is **disabled** unless validation passes (`can_lodge`).
  On lodge: set every diagnosis `status="lodged"`, claim `status="lodged"`, `decision="Received"`.
- After lodge, a **Simulate ACC decision** control (Accepted/Held/Declined) sets
  `status` and `decision` accordingly (accepted/held/declined).

### 7.10 Post-lodgement diagnosis change (Review → dialog)
- Only when lodged. Info banner explains it's a **Change-in-Diagnosis request** (not a
  re-lodgement) and must be the **same accident**.
- Fields: terminology search + select, body side, read-only accident date, reason,
  **same-event** checkbox (required to submit), "attach to ACC18" checkbox (default on).
- If same-event unchecked: warn to lodge a new ACC45 instead; submit disabled.
- On submit: append a ChangeRequest (`kind=add`, `status=submitted`, `bundled` per toggle),
  and append a Diagnosis with `status=change_pending` linked via `source_request`.

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

The lodge control must be **disabled** while any error exists; in a real build, re-validate
server-side at lodge so a stale client cannot bypass the gate.

---

## 9. Screen specifications

### 9.1 Dashboard — "My ACC submissions" (per-user, 14-day window)
The dashboard is the individual user's submission workspace, scoped to `created_by ==
current user`, and organised around the **14-day edit/revision/repair window**
(`EDIT_WINDOW_DAYS = 14`).

- Brand header bar with the signed-in user + role.
- Heading **"My ACC submissions"** and a note that referrals are kept 14 days for update/revision/repair, then drop off the active list.
- **Summary metric strip:** Active · Drafts to finish · Ready to lodge · Awaiting ACC · Needs repair (amber/red when >0) · Expiring ≤3 days (amber when >0).
- Primary button **"➕ New ACC45 claim (from PMS encounter)"**.
- **Active submissions** (`days_left > 0`), **sorted most-urgent-first** (ascending days left). Columns: `ACC45 no.` (mono), `Patient` (+ "needs action" pill for draft/held/declined), `Status` (pill), `Accident`, **`Edit window`** (see below), and **Open**.
- **Expired** (`days_left ≤ 0`) in a collapsed, read-only expander ("past 14-day window"); rows open in **View** (read-only) mode.

**Edit-window rules.**
- `days_left(claim) = 14 − (today − created).days`; `is_expired = days_left ≤ 0`.
- **Edit-window pill:** neutral/blue normally; **amber ≤ 7 days**; **red ≤ 3 days**; "Edit window expired" at ≤ 0.
- When expired, the claim is **read-only**: the workspace shows a read-only banner, the clinician diagnosis grid is locked, and **lodging is disabled**. (Ongoing certification would continue via a new ACC18, out of this window.)

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
work · Part D / ACC18**; **Practitioner declaration · Part E** (role-gated).

### 9.5 Review & lodge tab (in this order)
1. **Lodgement readiness** card (errors/warnings + lodge button when draft/ready).
2. **Full ACC45 summary** (§10) — appears directly under readiness, for every state.
3. **Post-lodgement** card — only when lodged: lodged banner + decision, Simulate ACC
   decision buttons (while `lodged`), "Add / change diagnosis (post-lodgement)" action,
   and a change-requests table.

### 9.6 Dialogs
- **Add diagnosis:** scope toggle, search, result select, eligibility banner, body-side radio, "Add to claim".
- **Add diagnosis to lodged ACC45:** info banner, search/select, body-side, read-only accident date, reason, same-event checkbox (required), attach-to-ACC18 checkbox, "Submit change request".

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

1. **Seed load:** three claims appear — `IO16452` (draft), `IO16454` (ready), `IO16456` (accepted).
2. **Create:** "New claim" allocates the next `IO#####`, opens the workspace on the Administrative tab.
3. **Tabs:** three visible, readable tabs; clicking switches the panel; the active tab is visually distinct and legible.
4. **Eligibility gate — block:** a claim whose only diagnosis is non-eligible (e.g. `183932001` Presentation for social reasons) is **not lodgeable**; the readiness list contains "At least one ACC-eligible diagnosis is required to lodge." and the lodge button is disabled.
5. **Eligibility gate — pass:** adding one `acc=true` diagnosis (with all other required fields) enables lodging.
6. **Lodge:** lodging flips status to `lodged`, sets `decision=Received`, marks diagnoses `lodged`, and reveals the post-lodgement change action.
7. **Read-only after lodge:** the Clinician diagnosis grid is read-only once lodged.
8. **Post-lodgement change:** requires same-event; on submit, creates a ChangeRequest and a `change_pending` diagnosis row.
9. **Role gate:** switching to `limited` disables the Part E declaration with an explanatory banner.
10. **Review summary:** the Review tab shows the full ACC45 summary (all Part A–E sections with entered values) directly under Lodgement readiness, in every claim state.
11. **Layout:** the app header and controls are not obscured by the top chrome.
12. **14-day window:** the dashboard shows a per-user working set; a referral ≤3 days from expiry shows a red edit-window pill and counts in "Expiring ≤3 days"; a referral past 14 days is absent from the active list, appears in the read-only Expired section, opens read-only, and cannot be edited or lodged.

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
| `audit` | `record(actor, action, detail)` | append-only audit (FHIR AuditEvent) | stub |
| `persistence` | `save(claim)`, `load_all()` | NZ-region datastore | stub |
| `notification` | `send_decision_sms(...)` | messaging provider | stub |

Full gap analysis, standards, and go-live gate: **`PRODUCTION-READINESS.md`**. A replica
is *mockup-conformant* if it satisfies §§2–12 with stubs; *production-conformant* only when
the P0 connectors/standards in that document are met.

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
Single-file **Streamlit** app (`app.py`): state in `st.session_state`; tabs built from
buttons (not `st.tabs`) for reliability; dialogs via `st.dialog`; a Tailwind-style CSS
layer injected via `st.markdown` carrying the tokens in §11. Deploys on Streamlit
Community Cloud from GitHub (`requirements.txt`: `streamlit>=1.37`). None of this is
required to replicate — any stack that satisfies §§2–12 is conformant.
