"""
ACC Claim Console — Streamlit mockup
=====================================
Two-role console for lodging NZ ACC injury claims (ACC45) and medical
certificates (ACC18). Front-end mockup only: ACC lodgement and SNOMED
terminology are stubbed. See README.md.

Run locally:   streamlit run app.py
Deploy:        push to GitHub, then Streamlit Community Cloud → New app.
"""

import random
import string
from datetime import date, datetime

import streamlit as st

st.set_page_config(page_title="ACC Claim Console", page_icon="🩺", layout="wide")

# --------------------------------------------------------------------------
# Stubbed SNOMED CT terminology (acc-claim-reference-set membership).
# acc_eligible mirrors membership in the ACC claim reference value set.
# --------------------------------------------------------------------------
TERM = [
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

EMP_STATUSES = ["Not employed in NZ", "Retired", "Employee", "Self-employed", "Owner employee", "Other"]
SCENES = ["Home", "Work", "Road", "Sports facility", "School", "Other"]
EXERTION = ["", "Sedentary", "Light", "Medium", "Heavy", "Very heavy"]

CSS = """
<style>
  .chip{display:inline-block;padding:2px 9px;border-radius:999px;font-size:11px;font-weight:700;background:#eceff3;color:#5b6b7b}
  .chip.ok{background:#e4f5ea;color:#1a7f45}
  .chip.err{background:#fbe6e5;color:#b3261e}
  .chip.warn{background:#fdf2d8;color:#8a5a00}
  .chip.blue{background:#e2eefb;color:#0f4f8a}
  .bnr{padding:10px 12px;border-radius:6px;font-size:13px;margin:6px 0}
  .bnr.ok{background:#e4f5ea;color:#1a7f45}
  .bnr.err{background:#fbe6e5;color:#b3261e}
  .bnr.warn{background:#fdf2d8;color:#8a5a00}
  .bnr.info{background:#eaf6fb;color:#0f4f8a}
  .lock{font-size:12px;color:#8a5a00;background:#fdf2d8;padding:3px 8px;border-radius:5px}
  .hd{color:#0f4f8a;font-weight:700}
</style>
"""


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def uid():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=7))


def allocate_number():
    n = "IO" + str(st.session_state.seq)
    st.session_state.seq += 1
    return n


def new_claim():
    """Simulate a claim launched from a PAS/PMS encounter and allocate an ACC45 number."""
    return {
        "id": uid(),
        "reference": allocate_number(),
        "number_source": "acc_allocation_api",
        "status": "draft",
        "decision": None,
        "encounter": {
            "external_id": "ENC-" + str(random.randint(100000, 999999)),
            "source": "pms_context",
            "facility": "Riverside Medical Centre",
            "provider": "Dr A. Rangi (GP)",
            "klass": "Outpatient / GP consult",
            "source_system": "Medtech PMS",
        },
        "patient": {
            "pas_id": "PAS-88213", "given": "Margaret", "family": "Ellery",
            "dob": "1949-03-11", "nhi": "JBX4728", "mobile": "021 555 0192",
            "email": "", "address": "14 Rewi Street, Christchurch 8022",
        },
        "employment": {"status": "Not employed in NZ", "occupation": "Unemployed", "employer": ""},
        "accident": {
            "adate": None, "atime": "08:34", "location": "Christchurch City",
            "scene": "Home", "workplace": "No", "vehicle": "No", "sporting": "No", "cause": "",
        },
        "consent": {"given": False, "at": None},
        "diagnoses": [],
        "flags": {"gradual": "No", "treatment": "No", "admitted": "No", "home": "No"},
        "capacity": {"exertion": "", "state": "", "restrictions": "", "justification": "",
                     "cert_type": "ACC45 initial (≤14 days)", "valid_from": None, "valid_to": None},
        "declaration": {"made": False, "date": None, "by": None, "provider_no": ""},
        "change_requests": [],
    }


def validate(c):
    errs, warns = [], []
    p, a = c["patient"], c["accident"]
    if not p["given"] or not p["family"]:
        errs.append("Patient name is required.")
    if not p["dob"]:
        errs.append("Date of birth is required.")
    if not a["adate"]:
        errs.append("Accident date is required.")
    if not a["cause"].strip():
        errs.append("Cause of injury is required.")
    if not c["consent"]["given"]:
        errs.append("Patient consent (all three authorisations) must be recorded.")
    if len(c["diagnoses"]) == 0:
        errs.append("At least one injury diagnosis is needed.")
    eligible = [d for d in c["diagnoses"] if d["acc"]]
    if c["diagnoses"] and not eligible:
        errs.append("At least one ACC-eligible diagnosis is required to lodge.")
    for d in c["diagnoses"]:
        if not d["side"]:
            errs.append(f'Diagnosis "{d["display"]}" needs a body side (or N/A).')
    cap = c["capacity"]
    if cap["state"] == "Fit for selected work" and not cap["restrictions"].strip():
        errs.append("Fit for selected work requires restrictions/activities.")
    if cap["state"] == "Fully unfit" and not cap["justification"].strip():
        errs.append("Fully unfit requires a justification.")
    if not c["declaration"]["made"]:
        errs.append("Practitioner declaration (Part E) must be completed by an eligible signer.")
    if not c["declaration"]["provider_no"]:
        errs.append("Provider number is required.")
    if not p["nhi"]:
        warns.append("No NHI supplied — slows processing.")
    if not p["mobile"]:
        warns.append("No mobile — patient won't get an SMS decision.")
    return errs, warns, (len(errs) == 0)


def active_claim():
    return next((c for c in st.session_state.claims if c["id"] == st.session_state.active), None)


def status_chip(status):
    m = {"draft": ("chip", "Draft"), "ready": ("chip blue", "Ready to lodge"),
         "lodged": ("chip blue", "Lodged"), "accepted": ("chip ok", "Accepted"),
         "held": ("chip warn", "Held"), "declined": ("chip err", "Declined")}
    cls, lab = m.get(status, ("chip", status))
    return f'<span class="{cls}">{lab}</span>'


# --------------------------------------------------------------------------
# session state init
# --------------------------------------------------------------------------
if "claims" not in st.session_state:
    st.session_state.claims = []
    st.session_state.active = None
    st.session_state.role = "prescriber"
    st.session_state.seq = 16457

st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# dialogs
# --------------------------------------------------------------------------
@st.dialog("Add diagnosis")
def add_diagnosis_dialog(c):
    scoped = st.checkbox("Scope to ACC-claimable concepts", value=True)
    q = st.text_input("Search SNOMED CT", placeholder="e.g. sprain, wrist, laceration, knee")
    pool = [t for t in TERM if (t["acc"] or not scoped)]
    if q.strip():
        pool = [t for t in pool if q.lower() in t["display"].lower() or q in t["code"]]
    if not pool:
        st.info("No matches.")
        return
    labels = [f'{t["display"]} · {t["code"]} · {"ACC-eligible" if t["acc"] else "NOT ACC-eligible"}' for t in pool]
    idx = st.selectbox("Result", range(len(pool)), format_func=lambda i: labels[i])
    sel = pool[idx]
    if sel["acc"]:
        st.markdown(f'<div class="bnr ok">✓ <b>{sel["display"]}</b> ({sel["code"]}) — member of the ACC '
                    f'claim reference set. Supports an ACC claim.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bnr err">⚠ <b>{sel["display"]}</b> ({sel["code"]}) — <b>not</b> in the ACC '
                    f'claim reference set. Can be recorded, but cannot support an ACC claim on its own. '
                    f'Consider a specific injury + body site.</div>', unsafe_allow_html=True)
    side = st.radio("Body side", ["Left", "Right", "Bilateral", "N/A"], horizontal=True)
    if st.button("Add to claim", type="primary"):
        c["diagnoses"].append({
            "id": uid(), "code": sel["code"], "display": sel["display"], "site": sel["site"],
            "side": side, "acc": sel["acc"], "primary": len(c["diagnoses"]) == 0, "status": "draft",
        })
        st.rerun()


@st.dialog("Add diagnosis to lodged ACC45")
def change_request_dialog(c):
    st.markdown('<div class="bnr info">ℹ This creates a <b>Change-in-Diagnosis request</b> against the '
                'existing claim (not a re-lodgement). The new injury must be from the <b>same accident</b> '
                'already on this ACC45. It receives its own cover decision.</div>', unsafe_allow_html=True)
    q = st.text_input("Search SNOMED CT", placeholder="e.g. knee, sprain")
    pool = TERM if not q.strip() else [t for t in TERM if q.lower() in t["display"].lower() or q in t["code"]]
    if not pool:
        st.info("No matches.")
        return
    labels = [f'{t["display"]} · {t["code"]} · {"ACC-eligible" if t["acc"] else "NOT ACC-eligible"}' for t in pool]
    idx = st.selectbox("Result", range(len(pool)), format_func=lambda i: labels[i])
    sel = pool[idx]
    side = st.radio("Body side", ["Left", "Right", "Bilateral", "N/A"], horizontal=True)
    st.text_input("Accident date (read-only)", value=str(c["accident"]["adate"] or "—"), disabled=True)
    reason = st.text_area("Reason for adding", placeholder="e.g. knee injured in the same fall, found on follow-up")
    same_event = st.checkbox("This injury was caused by the accident already on this claim (same event)")
    bundle = st.checkbox("Attach to the ACC18 medical certificate issued this encounter", value=True)
    if not same_event:
        st.markdown('<div class="bnr warn">⚠ If this injury is from a <b>different</b> accident, don\'t add it '
                    'here — lodge a new ACC45 instead.</div>', unsafe_allow_html=True)
    if st.button("Submit change request", type="primary", disabled=not same_event):
        req = {"id": uid(), "kind": "add", "code": sel["code"], "display": sel["display"], "side": side,
               "acc": sel["acc"], "same_event": same_event,
               "bundled": "ACC18 medical certificate" if bundle else "—", "reason": reason, "status": "submitted"}
        c["change_requests"].append(req)
        c["diagnoses"].append({"id": uid(), "code": sel["code"], "display": sel["display"], "site": sel["site"],
                               "side": side, "acc": sel["acc"], "primary": False, "status": "change_pending",
                               "source_request": req["id"]})
        st.rerun()


# --------------------------------------------------------------------------
# panels
# --------------------------------------------------------------------------
def dashboard():
    st.subheader("Claims")
    st.markdown('<div class="bnr info">➕ <b>New claim launches in encounter context.</b> In production this '
                'opens from the PAS/PMS against a live visit; here it simulates a Medtech PMS encounter for '
                'Margaret Ellery and allocates a fresh ACC45 number.</div>', unsafe_allow_html=True)
    if st.button("➕ New ACC45 claim (from PMS encounter)", type="primary"):
        c = new_claim()
        st.session_state.claims.append(c)
        st.session_state.active = c["id"]
        st.rerun()

    if not st.session_state.claims:
        st.caption("No claims yet — create one above.")
        return
    h = st.columns([1.2, 1.6, 1.4, 1.4, 1.1, 0.8])
    for col, t in zip(h, ["ACC45 no.", "Patient", "Encounter", "Accident date", "Status", ""]):
        col.markdown(f"**{t}**")
    for c in st.session_state.claims:
        cols = st.columns([1.2, 1.6, 1.4, 1.4, 1.1, 0.8])
        cols[0].write(c["reference"])
        cols[1].write(f'{c["patient"]["given"]} {c["patient"]["family"]}')
        cols[2].caption(c["encounter"]["external_id"])
        cols[3].write(str(c["accident"]["adate"] or "—"))
        cols[4].markdown(status_chip(c["status"]), unsafe_allow_html=True)
        if cols[5].button("Open", key="open_" + c["id"]):
            st.session_state.active = c["id"]
            st.rerun()


def admin_panel(c):
    st.markdown('<span class="hd">Encounter context (from PAS/PMS)</span>', unsafe_allow_html=True)
    e = c["encounter"]
    st.caption(f'Encounter {e["external_id"]} · Source {e["source_system"]} · Facility {e["facility"]} · '
               f'Provider {e["provider"]} · {e["klass"]}')
    st.caption(f'Patient identity inherited from the PMS — verify, don\'t re-key. ACC45 number allocated at '
               f'claim creation ({"ACC Claim Number Allocation API" if c["number_source"]=="acc_allocation_api" else "pre-allocated block"}).')
    st.divider()

    left, right = st.columns(2)
    with left:
        st.markdown('<span class="hd">Patient details — ACC45 Part A</span>', unsafe_allow_html=True)
        p = c["patient"]
        p["given"] = st.text_input("Given name *", value=p["given"])
        p["family"] = st.text_input("Family name *", value=p["family"])
        p["dob"] = st.text_input("Date of birth * (YYYY-MM-DD)", value=p["dob"])
        p["nhi"] = st.text_input("NHI", value=p["nhi"]).upper()
        p["mobile"] = st.text_input("Mobile", value=p["mobile"])
        p["email"] = st.text_input("Email", value=p["email"])
        p["address"] = st.text_input("Address", value=p["address"])
    with right:
        st.markdown('<span class="hd">Employment — ACC45 Part B</span>', unsafe_allow_html=True)
        em = c["employment"]
        em["status"] = st.selectbox("Employment status", EMP_STATUSES, index=EMP_STATUSES.index(em["status"]))
        em["occupation"] = st.text_input("Occupation", value=em["occupation"],
                                         disabled=em["status"] == "Not employed in NZ")
        em["employer"] = st.text_input("Employer", value=em["employer"], disabled=em["status"] != "Employee",
                                       placeholder="Required for employees" if em["status"] == "Employee" else "n/a")

    st.divider()
    st.markdown('<span class="hd">Accident details — ACC45 Part B</span>', unsafe_allow_html=True)
    a = c["accident"]
    a1, a2 = st.columns(2)
    with a1:
        a["adate"] = st.date_input("Date of accident *", value=a["adate"] or date(2026, 7, 7))
        a["atime"] = st.text_input("Time", value=a["atime"])
        a["location"] = st.text_input("Location", value=a["location"])
        a["scene"] = st.selectbox("Accident scene", SCENES, index=SCENES.index(a["scene"]))
    with a2:
        a["workplace"] = st.radio("Workplace accident?", ["No", "Yes"],
                                  horizontal=True, index=["No", "Yes"].index(a["workplace"]))
        a["vehicle"] = st.radio("Moving vehicle on road?", ["No", "Yes"],
                                horizontal=True, index=["No", "Yes"].index(a["vehicle"]))
        a["sporting"] = st.radio("Sporting injury?", ["No", "Yes"],
                                 horizontal=True, index=["No", "Yes"].index(a["sporting"]))
    a["cause"] = st.text_area("Cause of injury (mechanism) *", value=a["cause"],
                              placeholder="e.g. walking to the kitchen – tripped over own feet – fell to ground")

    st.divider()
    st.markdown('<span class="hd">Patient consent — ACC45 Part E (patient portion)</span>', unsafe_allow_html=True)
    if c["consent"]["given"]:
        st.markdown(f'<div class="bnr ok">✓ <b>Consent given</b> — recorded {c["consent"]["at"]}. '
                    f'All three authorisations captured.</div>', unsafe_allow_html=True)
    else:
        st.caption("Read the three-question consent script and record the response: "
                   "(1) authorise collection/use/disclosure, (2) declare true & correct, (3) authorise lodgement.")
        if st.button("Record patient consent (all three = Yes)", type="primary"):
            c["consent"] = {"given": True, "at": datetime.now().strftime("%d/%m/%Y %H:%M")}
            st.rerun()


def clinician_panel(c):
    role = st.session_state.role
    is_prescriber = role == "prescriber"
    locked = c["status"] not in ("draft", "ready")

    st.markdown('<span class="hd">Context (from admin / encounter)</span>', unsafe_allow_html=True)
    consent_chip = '<span class="chip ok">recorded</span>' if c["consent"]["given"] else '<span class="chip err">missing</span>'
    st.markdown(f'Patient: <b>{c["patient"]["given"]} {c["patient"]["family"]}</b> ({c["patient"]["dob"]}) · '
                f'Accident: <b>{c["accident"]["adate"] or "— not set"}</b> · Scene: <b>{c["accident"]["scene"]}</b> · '
                f'Consent: {consent_chip}', unsafe_allow_html=True)
    st.divider()

    # diagnosis grid
    st.markdown('<span class="hd">Injury diagnosis &amp; assistance — ACC45 Part C</span>', unsafe_allow_html=True)
    eligible = [d for d in c["diagnoses"] if d["acc"]]
    st.markdown(f'<span class="chip blue">{len(c["diagnoses"])} diagnoses · {len(eligible)} ACC-eligible</span>',
                unsafe_allow_html=True)
    if not locked:
        if st.button("➕ Add / change diagnosis"):
            add_diagnosis_dialog(c)
    else:
        st.markdown('<span class="lock">Lodged — grid read-only. Use the Review tab to add a post-lodgement '
                    'diagnosis change.</span>', unsafe_allow_html=True)

    if c["diagnoses"]:
        hdr = st.columns([3, 1, 1.2, 1.2, 0.9])
        for col, t in zip(hdr, ["Diagnosis", "Side", "ACC?", "Status", ""]):
            col.markdown(f"**{t}**")
        for d in c["diagnoses"]:
            row = st.columns([3, 1, 1.2, 1.2, 0.9])
            row[0].markdown(f'{d["display"]} <span class="chip">{d["code"]}</span>'
                            + (' <span class="chip blue">primary</span>' if d.get("primary") else ""),
                            unsafe_allow_html=True)
            row[1].write(d["side"])
            row[2].markdown('<span class="chip ok">Yes</span>' if d["acc"] else '<span class="chip err">Not eligible</span>',
                            unsafe_allow_html=True)
            row[3].markdown(f'<span class="chip">{d["status"]}</span>', unsafe_allow_html=True)
            if not locked:
                if row[4].button("Remove", key="del_" + d["id"]):
                    c["diagnoses"] = [x for x in c["diagnoses"] if x["id"] != d["id"]]
                    st.rerun()
    else:
        st.markdown('<div class="bnr err">✱ At least one injury diagnosis is needed.</div>', unsafe_allow_html=True)

    if c["diagnoses"] and not eligible:
        st.markdown('<div class="bnr err">⚠ <b>No ACC-eligible diagnosis yet.</b> Every diagnosis on this claim '
                    'is outside the ACC claim reference set. Add at least one ACC-eligible injury to lodge — '
                    'this claim cannot be submitted as-is.</div>', unsafe_allow_html=True)

    st.divider()
    # clinical flags
    st.markdown('<span class="hd">Clinical flags</span>', unsafe_allow_html=True)
    f = c["flags"]
    fc1, fc2 = st.columns(2)
    yn = ["No", "Yes"]
    f["gradual"] = fc1.radio("Work-related gradual process?", yn, horizontal=True, index=yn.index(f["gradual"]))
    f["treatment"] = fc1.radio("Treatment injury?", yn, horizontal=True, index=yn.index(f["treatment"]))
    f["home"] = fc2.radio("Home assistance required?", yn, horizontal=True, index=yn.index(f["home"]))
    f["admitted"] = fc2.radio("Patient admitted?", yn, horizontal=True, index=yn.index(f["admitted"]))
    if f["treatment"] == "Yes":
        st.markdown('<div class="bnr warn">ℹ Treatment injury — an ACC2152 and relevant patient notes are '
                    'required before lodgement.</div>', unsafe_allow_html=True)
    if f["gradual"] == "Yes":
        st.markdown('<div class="bnr warn">ℹ Gradual process — only a medical practitioner may lodge; '
                    'employment/work history needed.</div>', unsafe_allow_html=True)

    st.divider()
    # ability to work
    st.markdown('<span class="hd">Ability to work — ACC45 Part D / ACC18 certificate</span>', unsafe_allow_html=True)
    cap = c["capacity"]
    cap["exertion"] = st.selectbox("Normal work exertion", EXERTION, index=EXERTION.index(cap["exertion"]))
    states = ["", "Fully fit", "Fit for selected work", "Fully unfit"]
    cap["state"] = st.radio("Work capacity", states, horizontal=True, index=states.index(cap["state"]),
                            format_func=lambda s: s or "—")
    if cap["state"] == "Fit for selected work":
        cap["restrictions"] = st.text_area("Restrictions / activities & type of work *", value=cap["restrictions"],
                                           placeholder="e.g. seated duties only, no lifting >5kg, max 4 hrs/day")
    if cap["state"] == "Fully unfit":
        cap["justification"] = st.text_area("Justification (return to work would risk health/safety) *",
                                            value=cap["justification"])
    cc1, cc2 = st.columns(2)
    cert_types = ["ACC45 initial (≤14 days)", "ACC18 (beyond 14 days)"]
    cap["cert_type"] = cc1.selectbox("Certificate type", cert_types, index=cert_types.index(cap["cert_type"]))
    cap["valid_from"] = cc2.date_input("Valid from", value=cap["valid_from"] or date.today())
    cap["valid_to"] = cc2.date_input("Valid to", value=cap["valid_to"] or date.today())
    if cap["state"] in ("Fit for selected work", "Fully unfit"):
        st.caption("With prior earnings, this certification may make the patient eligible for weekly "
                   "compensation (informational — not a benefit decision).")

    st.divider()
    # declaration
    st.markdown('<span class="hd">Practitioner declaration — ACC45 Part E</span>', unsafe_allow_html=True)
    if not is_prescriber:
        st.markdown('<div class="bnr warn">🔒 <b>Part E is restricted to doctors and nurse practitioners.</b> '
                    'You are signed in as a limited-scope provider — switch role to a prescriber in the sidebar '
                    'to sign, or route to an eligible colleague.</div>', unsafe_allow_html=True)
    st.caption("I certify that I have personally examined the patient, that the condition is the result of an "
               "accident, and that the patient has authorised me to lodge this claim.")
    dec = c["declaration"]
    dec["provider_no"] = st.text_input("Provider number", value=dec["provider_no"],
                                       placeholder="e.g. HP-44921", disabled=not is_prescriber)
    if dec["made"]:
        st.markdown(f'<div class="bnr ok">✓ Declaration made {dec["date"]} by {dec["by"]}.</div>',
                    unsafe_allow_html=True)
    else:
        if st.button("Complete declaration (Today)", type="primary", disabled=not is_prescriber):
            dec["made"] = True
            dec["date"] = date.today().isoformat()
            dec["by"] = "Dr A. Rangi"
            if not dec["provider_no"]:
                dec["provider_no"] = "HP-44921"
            st.rerun()


def review_panel(c):
    errs, warns, can = validate(c)
    st.markdown('<span class="hd">Lodgement readiness</span>', unsafe_allow_html=True)
    if not errs:
        st.markdown('<div class="bnr ok">✓ All mandatory requirements met — ready to lodge.</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="bnr err"><b>Cannot lodge yet:</b><ul>'
                    + "".join(f"<li>{e}</li>" for e in errs) + "</ul></div>", unsafe_allow_html=True)
    if warns:
        st.markdown('<div class="bnr warn"><b>Warnings (non-blocking):</b><ul>'
                    + "".join(f"<li>{w}</li>" for w in warns) + "</ul></div>", unsafe_allow_html=True)

    if c["status"] in ("draft", "ready"):
        st.caption("Validation passed." if can else "Complete is disabled until validation passes.")
        if st.button("Complete & lodge ACC45", type="primary", disabled=not can):
            for d in c["diagnoses"]:
                d["status"] = "lodged"
            c["status"] = "lodged"
            c["decision"] = "Received"
            st.rerun()
        return

    # lodged view
    st.markdown(f'<div class="bnr info">✓ ACC45 lodged. Decision: <b>{c["decision"]}</b>. Diagnosis grid is now '
                f'read-only; further clinical changes go through a diagnosis-change request.</div>',
                unsafe_allow_html=True)
    if c["status"] == "lodged":
        st.caption("Simulate ACC decision:")
        d1, d2, d3, _ = st.columns([1, 1, 1, 4])
        if d1.button("Accepted"):
            c["status"] = "accepted"; c["decision"] = "Accepted"; st.rerun()
        if d2.button("Held"):
            c["status"] = "held"; c["decision"] = "Held"; st.rerun()
        if d3.button("Declined"):
            c["status"] = "declined"; c["decision"] = "Declined"; st.rerun()

    st.markdown("**Diagnoses of record**")
    for d in c["diagnoses"]:
        row = st.columns([3, 1, 1.2, 1.4])
        row[0].markdown(f'{d["display"]} <span class="chip">{d["code"]}</span>', unsafe_allow_html=True)
        row[1].write(d["side"])
        row[2].markdown('<span class="chip ok">Yes</span>' if d["acc"] else '<span class="chip err">No</span>',
                        unsafe_allow_html=True)
        row[3].markdown(f'<span class="chip">{d["status"]}</span>', unsafe_allow_html=True)

    if st.button("➕ Add / change diagnosis (post-lodgement)", type="primary"):
        change_request_dialog(c)

    if c["change_requests"]:
        st.markdown("**Diagnosis change requests**")
        for r in c["change_requests"]:
            st.write(f'• {r["kind"]} — {r["display"]} ({r["code"]}) · same event: '
                     f'{"✓" if r["same_event"] else "—"} · bundled: {r["bundled"]} · status: {r["status"]}')


def workspace(c):
    if st.button("← Home"):
        st.session_state.active = None
        st.rerun()
    st.markdown(f'### ACC45 {c["reference"]} &nbsp; {status_chip(c["status"])}', unsafe_allow_html=True)
    st.caption(f'{c["patient"]["given"]} {c["patient"]["family"]} · encounter {c["encounter"]["external_id"]}')
    tab_admin, tab_clin, tab_review = st.tabs(["Administrative", "Clinician", "Review & lodge"])
    with tab_admin:
        admin_panel(c)
    with tab_clin:
        clinician_panel(c)
    with tab_review:
        review_panel(c)


# --------------------------------------------------------------------------
# sidebar (role) + router
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ACC Claim Console")
    st.caption("research mockup — stubbed ACC & terminology")
    roles = {"prescriber": "Dr A. Rangi — GP (prescriber)",
             "limited": "J. Neho — Physiotherapist (limited)",
             "admin": "R. Patel — Reception (admin)"}
    st.session_state.role = st.radio("Signed in as", list(roles.keys()),
                                     format_func=lambda r: roles[r],
                                     index=list(roles).index(st.session_state.role))

c = active_claim()
if c is None:
    dashboard()
else:
    workspace(c)
