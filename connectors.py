"""
connectors.py — external integration seams for the ACC Claim Console.
=====================================================================

PRODUCTION READINESS: every boundary between this app and the Health New Zealand
digital ecosystem lives here as a **named connector with a STUB implementation**.
Each stub reproduces the mockup's current behaviour and documents the *real* service,
standard, and what a production build must implement. Swapping a stub for a real client
should require no change to app.py — only the body of these methods.

Set CONNECTOR_MODE per connector to "stub" (default) or "live"; live paths raise
NotImplementedError until wired. See PRODUCTION-READINESS.md for the full gap analysis.

This module is intentionally free of Streamlit and UI code so it is portable and testable.
"""

from __future__ import annotations

import copy
import re
from datetime import datetime

# Which connectors are stubbed vs live. Flip to "live" as real clients are wired.
CONNECTOR_MODE = {
    "auth": "stub",          # My Health Account Workforce (OIDC)
    "nhi": "stub",           # NHI FHIR API (Health NZ Digital Services Hub)
    "hpi": "stub",           # HPI FHIR API (Health NZ Digital Services Hub)
    "pms": "stub",           # PMS/PAS launch context (SMART on FHIR)
    "sdhr": "stub",          # Shared Digital Health Record (national shared record; replaces Hira)
    "terminology": "stub",   # SNOMED CT NZ Edition terminology server (NZHTS/Ontoserver)
    "acc": "stub",           # ACC eLodgement + Claim Number Allocation API
    "audit": "stub",         # immutable audit log
    "persistence": "stub",   # claim datastore (NZ data residency)
    "notification": "stub",  # SMS/email decision notifications
}


# ---------------------------------------------------------------------------
# 1. AUTH — workforce identity & authorisation
# ---------------------------------------------------------------------------
class AuthConnector:
    """
    Workforce sign-in, identity and role/scope authorisation.

    REAL SERVICE : Health NZ **My Health Account Workforce** (OIDC/OAuth2) — the
                   national workforce identity provider; RealMe for some flows.
    STANDARDS    : OpenID Connect; HISO identity standards; NZISM session controls.
    PRODUCTION   : validate ID/access tokens, map workforce identity → app role/scopes,
                   enforce MFA, session timeout, and per-action authorisation server-side.
                   The current in-app "role switcher" is a DEV-ONLY simulator and must be
                   removed in production.
    STATUS       : STUB — returns a simulated user chosen by the dev role switcher.
    """
    STUB = True
    # Role → capability matrix. In production these are workforce scopes/claims.
    ROLES = {
        "clerical": {"name": "R. Patel", "role_label": "Clerical / Reception",
                     "can_edit_admin": True, "can_edit_clinical": False, "can_submit": False,
                     "can_sign_part_e": False, "is_audit": False},
        "clinical": {"name": "Dr A. Rangi", "role_label": "Clinician",
                     "can_edit_admin": True, "can_edit_clinical": True, "can_submit": True,
                     "can_sign_part_e": True, "is_audit": False},
        "audit":    {"name": "M. Chen", "role_label": "Audit / Review",
                     "can_edit_admin": False, "can_edit_clinical": False, "can_submit": False,
                     "can_sign_part_e": False, "is_audit": True},
    }

    def current_user(self, simulated_role: str) -> dict:
        u = dict(self.ROLES.get(simulated_role, self.ROLES["clinical"]))
        u["role_key"] = simulated_role
        u["auth_source"] = "STUB — My Health Account Workforce"
        return u

    def _flag(self, role: str, key: str) -> bool:
        return self.ROLES.get(role, {}).get(key, False)

    def can_sign_part_e(self, role: str) -> bool:
        return self._flag(role, "can_sign_part_e")

    def can_submit(self, role: str) -> bool:
        return self._flag(role, "can_submit")

    def can_edit_admin(self, role: str) -> bool:
        return self._flag(role, "can_edit_admin")

    def can_edit_clinical(self, role: str) -> bool:
        return self._flag(role, "can_edit_clinical")

    def is_audit(self, role: str) -> bool:
        return self._flag(role, "is_audit")


# ---------------------------------------------------------------------------
# 2. NHI — patient identity & demographics
# ---------------------------------------------------------------------------
class NHIConnector:
    """
    National Health Index: validate an NHI and fetch verified demographics.

    REAL SERVICE : **NHI FHIR API** via the Health NZ **Digital Services Hub** (Patient
                   resource, NZ Base FHIR IG). Master source of patient identity in NZ.
                   (The Hira programme is superseded; NHI remains a national identity API.)
    STANDARDS    : HISO 10046 (NHI); NZ Base FHIR IG Patient profile. JIT retrieval only.
    PRODUCTION   : replace format check with the real HISO 10046 check-character
                   validation, and demographics with an authenticated NHI API lookup;
                   never cache beyond the consented purpose.
    STATUS       : STUB — regex format check only; no lookup.
    """
    STUB = True
    # legacy AAANNNN and new-format AAANNAA (letters exclude I and O)
    _LEGACY = re.compile(r"^[A-HJ-NP-Z]{3}\d{4}$")
    _NEW = re.compile(r"^[A-HJ-NP-Z]{3}\d{2}[A-HJ-NP-Z]{2}$")

    def validate(self, nhi: str) -> bool:
        if not nhi:
            return False
        nhi = nhi.strip().upper()
        # NOTE: real validation also verifies the HISO 10046 check character.
        return bool(self._LEGACY.match(nhi) or self._NEW.match(nhi))

    def lookup(self, nhi: str) -> dict | None:
        """Return verified demographics for an NHI. STUB: not available offline."""
        return None


# ---------------------------------------------------------------------------
# 3. HPI — provider / facility / organisation identity
# ---------------------------------------------------------------------------
class HPIConnector:
    """
    Health Provider Index: practitioner, organisation and facility identity.

    REAL SERVICE : **HPI FHIR API** via the Health NZ Digital Services Hub
                   (Practitioner/Organization/Location).
    STANDARDS    : HISO 10005/10006 (HPI); NZ Base FHIR IG. 170k+ practitioners.
    PRODUCTION   : resolve the signed-in workforce identity → HPI Practitioner (CPN),
                   confirm registration/scope of practice, and populate the provider
                   number/facility from HPI rather than free text.
    STATUS       : STUB — returns a fixed sample provider.
    """
    STUB = True

    def default_provider_number(self) -> str:
        return "HP-44921"

    def provider_lookup(self, provider_no: str) -> dict | None:
        return {"provider_no": provider_no, "name": "Dr A. Rangi", "scope": "General Practice",
                "source": "STUB — HPI FHIR API"} if provider_no else None


# ---------------------------------------------------------------------------
# 4. PMS / PAS — encounter (visit) launch context
# ---------------------------------------------------------------------------
class PMSConnector:
    """
    Patient Management / Administration System context for the current visit.

    REAL SERVICE : PMS/PAS vendor integration (Medtech, Indici, Profile, etc.) via a
                   **SMART on FHIR EHR launch** — the console opens in the context of an
                   existing Encounter and inherits patient + provider + facility.
    STANDARDS    : SMART App Launch; FHIR Encounter/Patient (NZ Base IG).
    PRODUCTION   : accept the launch token, resolve Encounter + Patient from the PMS FHIR
                   server, and reconcile the patient to NHI. No re-keying of identity.
    STATUS       : STUB — returns a simulated encounter + seed patient.
    """
    STUB = True

    def get_encounter_context(self) -> dict:
        import random
        return {
            "encounter": {
                "external_id": "ENC-" + str(random.randint(100000, 999999)),
                "source": "pms_context", "facility": "Riverside Medical Centre",
                "provider": "Dr A. Rangi (GP)", "klass": "Outpatient / GP consult",
                "source_system": "Medtech PMS (STUB)",
            },
            "patient": {
                "pas_id": "PAS-88213", "given": "Margaret", "family": "Ellery",
                "dob": "1949-03-11", "nhi": "JBX4728", "mobile": "021 555 0192",
                "email": "", "address": "14 Rewi Street, Christchurch 8022",
            },
        }


# ---------------------------------------------------------------------------
# 4b. SDHR — Shared Digital Health Record (national shared record)
# ---------------------------------------------------------------------------
class SDHRConnector:
    """
    National shared health record — read a patient's core health information and
    contribute clinical events (e.g. this encounter's diagnoses) to the shared record.

    REAL SERVICE : **Shared Digital Health Record (SDHR)** — Health NZ's national shared
                   record programme (supersedes the earlier Hira programme). Copies core
                   health info from the practice PMS into a central store, subject to the
                   patient's consent and existing access/privacy controls.
    STANDARDS    : **NZ SDHR FHIR API / IG** (fhir-ig.digital.health.nz/sdhr); NZ Base
                   FHIR IG. (Programme phasing in; general API availability is staged.)
    PRODUCTION   : with consent, read patient core health info to prefill/contextualise,
                   and contribute the lodged encounter/diagnoses to the shared record via
                   the SDHR API. Honour SDHR consent and access controls.
    STATUS       : STUB — no read/contribute; returns empty.
    """
    STUB = True

    def get_core_health_info(self, nhi: str) -> dict | None:
        return None  # not available in the mockup

    def contribute(self, claim: dict) -> bool:
        return False  # not contributed in the mockup


# ---------------------------------------------------------------------------
# 5. TERMINOLOGY — SNOMED CT NZ Edition + ACC claim reference set
# ---------------------------------------------------------------------------
class TerminologyConnector:
    """
    Diagnosis lookup + ACC-eligibility, bound to the ACC claim reference value set.

    REAL SERVICE : **SNOMED CT NZ Edition** terminology server (NZ Health Terminology
                   Service / Ontoserver) via FHIR ValueSet/$expand and $validate-code,
                   bound to https://nzhts.digital.health.nz/fhir/ValueSet/acc-claim-reference-set
    STANDARDS    : SNOMED CT NZ Edition (module 21000210109); FHIR R4 terminology ops.
    PRODUCTION   : replace this in-memory sample (15 concepts) with live $expand for
                   typeahead and $validate-code for the ACC? flag; pin & record the
                   value-set version at lodgement. See ACC-FHIR-Terminology-Spec.md.
    STATUS       : STUB — 15-concept sample of the value set.
    """
    STUB = True
    CONCEPTS = [
        {"code": "283384001", "display": "Sprain of ligament of ankle", "site": "Ankle", "acc": True},
        {"code": "262911006", "display": "Laceration of finger", "site": "Finger", "acc": True},
        {"code": "20946005", "display": "Fracture of distal radius (wrist)", "site": "Wrist", "acc": True},
        {"code": "82576008", "display": "Contusion of knee", "site": "Knee", "acc": True},
        {"code": "209815008", "display": "Sprain of rotator cuff (shoulder)", "site": "Shoulder", "acc": True},
        {"code": "312608009", "display": "Laceration - injury", "site": "", "acc": True},
        {"code": "110030002", "display": "Concussion injury of brain", "site": "Head", "acc": True},
        {"code": "125605004", "display": "Fracture of bone", "site": "", "acc": True},
        {"code": "44465007", "display": "Sprain of neck", "site": "Neck", "acc": True},
        {"code": "81680005", "display": "Closed fracture of shaft of tibia", "site": "Lower leg", "acc": True},
        {"code": "7200002", "display": "Alcohol dependence syndrome", "site": "", "acc": False},
        {"code": "73211009", "display": "Diabetes mellitus", "site": "", "acc": False},
        {"code": "38341003", "display": "Hypertensive disorder", "site": "", "acc": False},
        {"code": "48694002", "display": "Anxiety disorder", "site": "", "acc": False},
        {"code": "183932001", "display": "Presentation for social reasons", "site": "", "acc": False},
    ]
    VALUESET_VERSION = "20260401 (STUB)"

    def search(self, query: str = "", eligible_only: bool = True) -> list[dict]:
        """FHIR ValueSet/$expand equivalent (typeahead)."""
        pool = [c for c in self.CONCEPTS if (c["acc"] or not eligible_only)]
        q = (query or "").strip().lower()
        if q:
            pool = [c for c in pool if q in c["display"].lower() or q in c["code"]]
        return pool

    def is_acc_eligible(self, code: str) -> bool:
        """FHIR $validate-code equivalent against the ACC claim reference set."""
        return any(c["code"] == code and c["acc"] for c in self.CONCEPTS)


# ---------------------------------------------------------------------------
# 6. ACC — claim number allocation, eLodgement, decisions
# ---------------------------------------------------------------------------
class ACCConnector:
    """
    ACC claim number allocation, electronic lodgement, and cover decisions.

    REAL SERVICE : ACC **Developer Resource Centre** (developer.acc.co.nz), integrated
                   directly (this app is the ACC software vendor, not proxied via the PMS):
                   **Claim Number Allocation API** (on-demand ACC45 numbers), **Claim API**
                   (lodge ACC45/ACC18), **Query Claim Status API** (poll registration +
                   cover decision). ACC2152 for treatment injury. Auth = API key + Health
                   Secure Digital Certificate; a compliance (test) environment precedes prod.
    STANDARDS    : ACC provider integration specs; ACC45 number is an opaque string with
                   three valid formats (AB12345 / 12345AB / 1234ABC) — never parse it.
    PRODUCTION   : allocate a number at claim creation; submit the lodgement payload and
                   persist ACC's transport receipt (-> acknowledged_at); **poll** the Query
                   Claim Status API for the async cover decision (no webhook). See
                   PRODUCTION-READINESS.md F. Invoicing is out of scope.
    STATUS       : STUB — sequential IO##### numbers; lodge returns a receipt timestamp.
    """
    STUB = True

    def allocate_claim_number(self, seq: int) -> str:
        # Opaque string; format is ACC-owned and changing — do not parse elsewhere.
        return "IO" + str(seq)

    def lodge(self, claim: dict) -> str:
        """
        Submit the ACC45 and return a **transport-level acknowledgement** — the message
        reached ACC — after which ACC registers the claim. This is NOT a cover decision:
        ACC's documented cover statuses are accept / decline / held (held = under review,
        'pre-cover'), plus 'not applicable' while the claim is not yet registered. There
        is no 'Received' cover status. A cover decision arrives asynchronously.
        """
        return datetime.now().isoformat(timespec="seconds")

    def decision(self, choice: str) -> str:
        """A simulated cover decision. STUB only — real decisions arrive async."""
        return {"Accepted": "Accepted", "Held": "Held", "Declined": "Declined"}[choice]


# ---------------------------------------------------------------------------
# 7. AUDIT — immutable clinical/claim audit trail
# ---------------------------------------------------------------------------
class AuditConnector:
    """
    Tamper-evident audit log of every consent capture, edit, lodgement and access.

    REAL SERVICE : centralised, append-only audit store (e.g. FHIR AuditEvent) with
                   retention per records-management policy.
    STANDARDS    : Privacy Act 2020; Health Information Privacy Code 2020; HISO audit
                   expectations. Claims are legal records.
    PRODUCTION   : write who/what/when/why for every state change and every read of
                   patient data; make it immutable and independently reviewable.
    STATUS       : STUB — in-memory list (lost on restart). Each entry attributes the
                   change to its author (name + role) against a claim reference; the
                   audit view renders per-claim history on inspect.
    """
    STUB = True
    LOG: list[dict] = []

    def record(self, author: str, role: str, action: str, reference: str = "", detail: str = "") -> None:
        self.LOG.append({"ts": datetime.now().isoformat(timespec="seconds"),
                         "author": author, "role": role, "action": action,
                         "reference": reference, "detail": detail})

    def history(self, reference: str) -> list[dict]:
        """The attributed audit trail for one claim, oldest-first."""
        return [e for e in self.LOG if e["reference"] == reference]


# ---------------------------------------------------------------------------
# 8. PERSISTENCE — claim datastore
# ---------------------------------------------------------------------------
class PersistenceConnector:
    """
    Durable, multi-user, **auditable** claim store built around the claim aggregate.

    REAL SERVICE : a database (per architecture) hosted in an approved NZ region.
    STANDARDS    : NZ data residency/sovereignty; encryption at rest; backup/retention;
                   Māori Data Sovereignty (Te Mana Raraunga) considerations.
    PRODUCTION   : replace session-only state with a concurrency-safe store and optimistic
                   locking. Suggested schema (built around the dashboard's claim model):
                     • claim(reference PK, status, created, created_by, lodged_on, decision,
                             patient/employment/accident/consent/capacity/declaration/flags …)
                     • diagnosis(id, claim_ref FK, code, system, display, side, acc_eligible, status)
                     • change_request(id, claim_ref FK, kind, code, same_event, bundled, status)
                     • claim_version(reference FK, version, ts, author, role, action) — append-only,
                       one row per save, attributing every change to its author
                     • audit_event(ts, author, role, action, reference, detail) — see AuditConnector
                   Every save writes a new claim_version row (attribution) and an audit_event.
    STATUS       : STUB — in-memory latest snapshot + per-claim version history; each save
                   is attributed to its author and mirrored into the audit trail.
    """
    STUB = True
    STORE: dict = {}      # reference -> latest snapshot
    VERSIONS: dict = {}   # reference -> [ {version, ts, author, role, action} ]

    def save(self, claim: dict, author: str, role: str, action: str) -> int:
        ref = claim["reference"]
        v = len(self.VERSIONS.get(ref, [])) + 1
        self.VERSIONS.setdefault(ref, []).append({
            "version": v, "ts": datetime.now().isoformat(timespec="seconds"),
            "author": author, "role": role, "action": action})
        self.STORE[ref] = copy.deepcopy(claim)          # immutable-ish snapshot
        audit.record(author, role, action, ref, f"v{v}")  # mirror into audit trail
        return v

    def versions(self, reference: str) -> list[dict]:
        return self.VERSIONS.get(reference, [])

    def load_all(self) -> list[dict]:
        return list(self.STORE.values())


# ---------------------------------------------------------------------------
# 9. NOTIFICATION — patient / provider messaging
# ---------------------------------------------------------------------------
class NotificationConnector:
    """
    Outbound SMS/email (e.g. ACC cover-decision SMS to the patient).

    REAL SERVICE : an approved messaging provider / national notification service.
    STANDARDS    : consent to contact; Privacy Act 2020.
    PRODUCTION   : send templated, auditable notifications; respect contact preferences.
    STATUS       : STUB — no-op.
    """
    STUB = True

    def send_decision_sms(self, mobile: str, reference: str, decision: str) -> bool:
        return False  # not sent in the mockup


# Singleton instances imported by app.py
auth = AuthConnector()
nhi = NHIConnector()
hpi = HPIConnector()
pms = PMSConnector()
sdhr = SDHRConnector()
terminology = TerminologyConnector()
acc = ACCConnector()
audit = AuditConnector()
persistence = PersistenceConnector()
notification = NotificationConnector()
