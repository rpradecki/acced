"""
ACC Claim Console — Streamlit mockup
=====================================
Two-role console for lodging NZ ACC injury claims (ACC45) and medical
certificates (ACC18). Front-end mockup only: ACC lodgement and SNOMED
terminology are stubbed. See README.md.

Run locally:   streamlit run app.py
Deploy:        push to GitHub, then Streamlit Community Cloud → New app.

UI: a Tailwind-inspired CSS layer is injected via st.markdown (Streamlit strips
<script>/<link> and full Tailwind's reset fights Streamlit's base styles, so we
use a scoped design system with the Tailwind palette/spacing instead).
"""

import random
import string
from datetime import date, datetime

import streamlit as st

st.set_page_config(page_title="ACC Claim Console", page_icon="🩺", layout="wide")

# --------------------------------------------------------------------------
# Stubbed SNOMED CT terminology (acc-claim-reference-set membership).
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

# --------------------------------------------------------------------------
# Tailwind-inspired design system (scoped, injected once).
# --------------------------------------------------------------------------
CSS = """
<style>
  :root{
    --slate-50:#f8fafc; --slate-100:#f1f5f9; --slate-200:#e2e8f0; --slate-300:#cbd5e1;
    --slate-400:#94a3b8; --slate-500:#64748b; --slate-600:#475569; --slate-700:#334155;
    --slate-800:#1e293b; --slate-900:#0f172a;
    --blue-50:#eff6ff; --blue-100:#dbeafe; --blue-600:#2563eb; --blue-700:#1d4ed8; --blue-800:#1e40af;
    --green-50:#ecfdf5; --green-600:#059669; --green-700:#047857;
    --amber-50:#fffbeb; --amber-600:#d97706; --amber-700:#b45309;
    --red-50:#fef2f2; --red-200:#fecaca; --red-600:#dc2626; --red-700:#b91c1c;
    --green-200:#a7f3d0; --amber-200:#fde68a; --blue-200:#bfdbfe;
  }
  html, body, [class*="css"], .stMarkdown, p, span, div, label, input, textarea, select{
    font-size:13px;
  }
  .block-container{padding-top:1rem !important; padding-bottom:2.5rem !important; max-width:1180px;}
  [data-testid="stVerticalBlock"]{gap:.5rem;}
  [data-testid="stHorizontalBlock"]{gap:.55rem;}
  [data-testid="stElementContainer"]{margin-bottom:0 !important;}
  hr{margin:.5rem 0 !important; border-color:var(--slate-200);}
  h1,h2,h3,h4{letter-spacing:-.01em; color:var(--slate-900);}

  /* cards = bordered containers */
  [data-testid="stVerticalBlockBorderWrapper"]{
    background:#fff; border:1px solid var(--slate-200) !important; border-radius:12px;
    box-shadow:0 1px 2px rgba(15,23,42,.05); padding:2px 4px;
  }

  /* buttons */
  .stButton>button{
    border-radius:8px; border:1px solid var(--slate-300); background:#fff; color:var(--slate-700);
    padding:.34rem .8rem; font-weight:600; font-size:12.5px; transition:all .12s;
  }
  .stButton>button:hover{border-color:var(--slate-400); background:var(--slate-50);}
  .stButton>button[kind="primary"]{background:var(--blue-600); border-color:var(--blue-700); color:#fff;}
  .stButton>button[kind="primary"]:hover{background:var(--blue-700);}
  .stButton>button:disabled{background:var(--slate-100); color:var(--slate-400); border-color:var(--slate-200);}

  /* inputs — compact */
  .stTextInput input, .stDateInput input, .stNumberInput input{padding:.32rem .55rem !important; font-size:12.5px;}
  .stTextArea textarea{padding:.4rem .55rem !important; font-size:12.5px;}
  div[data-baseweb="select"]>div{min-height:34px; font-size:12.5px;}
  label p{font-size:11.5px !important; color:var(--slate-600) !important; font-weight:600 !important; margin-bottom:2px !important;}
  [data-testid="stWidgetLabel"]{margin-bottom:1px;}

  /* radio horizontal → segmented look */
  [role="radiogroup"]{gap:.4rem;}
  [role="radiogroup"] label{background:#fff; border:1px solid var(--slate-200); border-radius:7px; padding:2px 9px;}

  /* tabs — segmented control, unmistakably tab-like */
  [data-baseweb="tab-list"]{
    gap:4px; background:var(--slate-100); border:1px solid var(--slate-200);
    border-radius:10px; padding:4px; margin-bottom:.7rem;
  }
  [data-baseweb="tab"]{
    padding:8px 18px !important; font-weight:700; font-size:12.5px; color:var(--slate-500);
    background:transparent; border-radius:8px; transition:all .12s;
  }
  [data-baseweb="tab"]:hover{color:var(--slate-700); background:rgba(255,255,255,.55);}
  [data-baseweb="tab"][aria-selected="true"]{
    color:var(--blue-700); background:#fff; box-shadow:0 1px 2px rgba(15,23,42,.12);
  }
  [data-baseweb="tab-highlight"], [data-baseweb="tab-border"]{display:none;}

  /* sidebar dark */
  [data-testid="stSidebar"]{background:var(--slate-900);}
  [data-testid="stSidebar"] *{color:var(--slate-100) !important;}
  [data-testid="stSidebar"] [role="radiogroup"] label{background:var(--slate-800); border-color:var(--slate-700);}

  /* --- utility components --- */
  .apphdr{display:flex; align-items:center; gap:12px; padding:10px 16px; margin-bottom:10px;
    background:linear-gradient(90deg,var(--slate-900),var(--slate-800)); border-radius:12px; color:#fff;}
  .apphdr .brand{font-weight:800; letter-spacing:.2px; font-size:15px;}
  .apphdr .ref{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; background:rgba(255,255,255,.12);
    padding:2px 9px; border-radius:7px; font-size:12.5px;}
  .apphdr .sub{color:var(--slate-300); font-size:12px;}
  .apphdr .grow{flex:1;}

  .sec{font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:var(--slate-500);
    font-weight:800; margin:2px 0 6px;}
  .chips{display:flex; flex-wrap:wrap; gap:6px; margin:2px 0 6px;}
  .kv{background:var(--slate-50); border:1px solid var(--slate-200); border-radius:8px; padding:3px 9px;
    font-size:11.5px; color:var(--slate-500);}
  .kv b{color:var(--slate-800); font-weight:700;}
  .mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11px; color:var(--slate-400);}

  .pill{display:inline-block; padding:1px 8px; border-radius:999px; font-size:10.5px; font-weight:800;
    background:var(--slate-100); color:var(--slate-500); letter-spacing:.02em;}
  .pill.ok{background:var(--green-50); color:var(--green-700);}
  .pill.err{background:var(--red-50); color:var(--red-700);}
  .pill.warn{background:var(--amber-50); color:var(--amber-700);}
  .pill.blue{background:var(--blue-50); color:var(--blue-800);}

  .bnr{padding:8px 11px; border-radius:9px; font-size:12.5px; margin:5px 0; border:1px solid transparent; line-height:1.45;}
  .bnr.ok{background:var(--green-50); color:var(--green-700); border-color:var(--green-200);}
  .bnr.err{background:var(--red-50); color:var(--red-700); border-color:var(--red-200);}
  .bnr.warn{background:var(--amber-50); color:var(--amber-700); border-color:var(--amber-200);}
  .bnr.info{background:var(--blue-50); color:var(--blue-800); border-color:var(--blue-200);}
  .bnr ul{margin:4px 0 0 16px; padding:0;}

  table.tbl{width:100%; border-collapse:separate; border-spacing:0; font-size:12.5px; margin:2px 0 4px;}
  table.tbl th{background:var(--slate-50); color:var(--slate-500); text-align:left; padding:6px 10px;
    border-bottom:1px solid var(--slate-200); font-size:10px; text-transform:uppercase; letter-spacing:.05em; font-weight:800;}
  table.tbl td{padding:6px 10px; border-bottom:1px solid var(--slate-100); color:var(--slate-700); vertical-align:middle;}
  table.tbl tr:last-child td{border-bottom:0;}
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
    return {
        "id": uid(),
        "reference": allocate_number(),
        "number_source": "acc_allocation_api",
        "status": "draft",
        "decision": None,
        "encounter": {
            "external_id": "ENC-" + str(random.randint(100000, 999999)),
            "source": "pms_context", "facility": "Riverside Medical Centre",
            "provider": "Dr A. Rangi (GP)", "klass": "Outpatient / GP consult",
            "source_system": "Medtech PMS",
        },
        "patient": {"pas_id": "PAS-88213", "given": "Margaret", "family": "Ellery",
                    "dob": "1949-03-11", "nhi": "JBX4728", "mobile": "021 555 0192",
                    "email": "", "address": "14 Rewi Street, Christchurch 8022"},
        "employment": {"status": "Not employed in NZ", "occupation": "Unemployed", "employer": ""},
        "accident": {"adate": None, "atime": "08:34", "location": "Christchurch City",
                     "scene": "Home", "workplace": "No", "vehicle": "No", "sporting": "No", "cause": ""},
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


STATUS = {"draft": ("pill", "Draft"), "ready": ("pill blue", "Ready to lodge"),
          "lodged": ("pill blue", "Lodged"), "accepted": ("pill ok", "Accepted"),
          "held": ("pill warn", "Held"), "declined": ("pill err", "Declined")}


def status_pill(status):
    cls, lab = STATUS.get(status, ("pill", status))
    return f'<span class="{cls}">{lab}</span>'


def sec(title):
    st.markdown(f'<div class="sec">{title}</div>', unsafe_allow_html=True)


def html(s):
    st.markdown(s, unsafe_allow_html=True)


def dx_table(diags, with_status=True):
    head = "<tr><th>Diagnosis</th><th>Side</th><th>ACC?</th>" + ("<th>Status</th>" if with_status else "") + "</tr>"
    rows = ""
    for d in diags:
        acc = '<span class="pill ok">Yes</span>' if d["acc"] else '<span class="pill err">Not eligible</span>'
        prim = ' <span class="pill blue">primary</span>' if d.get("primary") else ""
        stt = f'<td><span class="pill">{d["status"]}</span></td>' if with_status else ""
        rows += (f'<tr><td>{d["display"]} <span class="mono">{d["code"]}</span>{prim}</td>'
                 f'<td>{d["side"]}</td><td>{acc}</td>{stt}</tr>')
    return f'<table class="tbl"><thead>{head}</thead><tbody>{rows}</tbody></table>'


# --------------------------------------------------------------------------
# sample (pre-saved) claims — openable & editable from the dashboard
# --------------------------------------------------------------------------
def _base(ref):
    return {
        "id": uid(), "reference": ref, "number_source": "acc_allocation_api",
        "status": "draft", "decision": None,
        "encounter": {"external_id": "ENC-" + str(random.randint(100000, 999999)), "source": "pms_context",
                      "facility": "Riverside Medical Centre", "provider": "Dr A. Rangi (GP)",
                      "klass": "Outpatient / GP consult", "source_system": "Medtech PMS"},
        "patient": {"pas_id": "", "given": "", "family": "", "dob": "", "nhi": "", "mobile": "", "email": "", "address": ""},
        "employment": {"status": "Not employed in NZ", "occupation": "Unemployed", "employer": ""},
        "accident": {"adate": None, "atime": "", "location": "", "scene": "Home",
                     "workplace": "No", "vehicle": "No", "sporting": "No", "cause": ""},
        "consent": {"given": False, "at": None},
        "diagnoses": [],
        "flags": {"gradual": "No", "treatment": "No", "admitted": "No", "home": "No"},
        "capacity": {"exertion": "", "state": "", "restrictions": "", "justification": "",
                     "cert_type": "ACC45 initial (≤14 days)", "valid_from": None, "valid_to": None},
        "declaration": {"made": False, "date": None, "by": None, "provider_no": ""},
        "change_requests": [],
    }


def _merge(c, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(c.get(k), dict):
            c[k].update(v)
        else:
            c[k] = v
    return c


def _dx(code, disp, side, acc, status="draft", primary=False):
    return {"id": uid(), "code": code, "display": disp, "site": "", "side": side,
            "acc": acc, "primary": primary, "status": status}


def seed_claims():
    # 1) In-progress DRAFT — consent + one diagnosis captured, but not yet certified/declared (mid-edit).
    c1 = _merge(_base("IO16452"), {
        "status": "draft",
        "patient": {"pas_id": "PAS-40021", "given": "Aroha", "family": "Ngata", "dob": "1991-06-02",
                    "nhi": "KLP2286", "mobile": "021 448 1190", "address": "9 Tui Lane, Christchurch 8014"},
        "employment": {"status": "Employee", "occupation": "Warehouse assistant", "employer": "Southern Distribution Ltd"},
        "accident": {"adate": date(2026, 7, 6), "atime": "14:20", "location": "Christchurch City", "scene": "Work",
                     "workplace": "Yes", "cause": "lifting a box off a pallet – felt sudden shoulder pain"},
        "consent": {"given": True, "at": "06/07/2026 14:40"},
        "diagnoses": [_dx("209815008", "Sprain of rotator cuff (shoulder)", "Right", True, "draft", True)],
    })
    # 2) READY to lodge — fully valid; open the Review tab to lodge it.
    c2 = _merge(_base("IO16454"), {
        "status": "ready",
        "patient": {"pas_id": "PAS-77310", "given": "David", "family": "Thorne", "dob": "1974-11-19",
                    "nhi": "MTR9043", "mobile": "027 220 6655", "address": "22 Kowhai Road, Rangiora 7400"},
        "employment": {"status": "Self-employed", "occupation": "Builder", "employer": ""},
        "accident": {"adate": date(2026, 7, 7), "atime": "09:05", "location": "Rangiora", "scene": "Home",
                     "cause": "slipped off a step ladder – landed awkwardly on left ankle"},
        "consent": {"given": True, "at": "07/07/2026 09:30"},
        "diagnoses": [_dx("283384001", "Sprain of ligament of ankle", "Left", True, "draft", True)],
        "capacity": {"exertion": "Heavy", "state": "Fit for selected work",
                     "restrictions": "seated/office duties only, no ladder work, no lifting >5kg, max 6 hrs/day",
                     "cert_type": "ACC18 (beyond 14 days)", "valid_from": date(2026, 7, 7), "valid_to": date(2026, 7, 21)},
        "declaration": {"made": True, "date": "2026-07-07", "by": "Dr A. Rangi", "provider_no": "HP-44921"},
    })
    # 3) LODGED / ACCEPTED — grid read-only; edit via post-lodgement diagnosis change in the Review tab.
    c3 = _merge(_base("IO16456"), {
        "status": "accepted", "decision": "Accepted",
        "patient": {"pas_id": "PAS-51188", "given": "Sina", "family": "Faleolo", "dob": "1998-02-27",
                    "nhi": "NBW7712", "mobile": "022 909 3312", "address": "5 Harakeke Street, Christchurch 8025"},
        "employment": {"status": "Employee", "occupation": "Chef", "employer": "Harbourview Restaurant"},
        "accident": {"adate": date(2026, 6, 30), "atime": "19:45", "location": "Christchurch City", "scene": "Work",
                     "workplace": "Yes", "cause": "slipped on wet kitchen floor – put out right hand to break the fall"},
        "consent": {"given": True, "at": "30/06/2026 20:10"},
        "diagnoses": [_dx("20946005", "Fracture of distal radius (wrist)", "Right", True, "accepted", True)],
        "capacity": {"exertion": "Medium", "state": "Fully unfit",
                     "justification": "wrist immobilised in cast; unable to perform any kitchen duties safely",
                     "cert_type": "ACC18 (beyond 14 days)", "valid_from": date(2026, 6, 30), "valid_to": date(2026, 7, 28)},
        "declaration": {"made": True, "date": "2026-06-30", "by": "Dr A. Rangi", "provider_no": "HP-44921"},
    })
    return [c1, c2, c3]


# --------------------------------------------------------------------------
# session state init
# --------------------------------------------------------------------------
if "claims" not in st.session_state:
    st.session_state.seq = 16457          # new claims continue after the seeded refs
    st.session_state.claims = seed_claims()
    st.session_state.active = None
    st.session_state.role = "prescriber"

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
        html(f'<div class="bnr ok">✓ <b>{sel["display"]}</b> ({sel["code"]}) — member of the ACC claim reference '
             f'set. Supports an ACC claim.</div>')
    else:
        html(f'<div class="bnr err">⚠ <b>{sel["display"]}</b> ({sel["code"]}) — <b>not</b> in the ACC claim '
             f'reference set. Can be recorded, but cannot support an ACC claim on its own. Consider a specific '
             f'injury + body site.</div>')
    side = st.radio("Body side", ["Left", "Right", "Bilateral", "N/A"], horizontal=True)
    if st.button("Add to claim", type="primary"):
        c["diagnoses"].append({"id": uid(), "code": sel["code"], "display": sel["display"], "site": sel["site"],
                               "side": side, "acc": sel["acc"], "primary": len(c["diagnoses"]) == 0, "status": "draft"})
        st.rerun()


@st.dialog("Add diagnosis to lodged ACC45")
def change_request_dialog(c):
    html('<div class="bnr info">ℹ This creates a <b>Change-in-Diagnosis request</b> against the existing claim '
         '(not a re-lodgement). The new injury must be from the <b>same accident</b> already on this ACC45. '
         'It receives its own cover decision.</div>')
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
        html('<div class="bnr warn">⚠ If this injury is from a <b>different</b> accident, don\'t add it here — '
             'lodge a new ACC45 instead.</div>')
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
    html('<div class="apphdr"><span class="brand">🩺 ACC Claim Console</span>'
         '<span class="sub">research mockup · stubbed ACC &amp; terminology</span><span class="grow"></span>'
         f'<span class="sub">{len(st.session_state.claims)} claim(s)</span></div>')
    with st.container(border=True):
        html('<div class="bnr info" style="margin:4px 6px">➕ <b>New claim launches in encounter context.</b> '
             'In production this opens from the PAS/PMS against a live visit; here it simulates a Medtech PMS '
             'encounter for Margaret Ellery and allocates a fresh ACC45 number.</div>')
        cc = st.columns([2, 5])
        if cc[0].button("➕ New ACC45 claim (from PMS encounter)", type="primary", use_container_width=True):
            c = new_claim()
            st.session_state.claims.append(c)
            st.session_state.active = c["id"]
            st.rerun()

    if not st.session_state.claims:
        st.caption("No claims yet — create one above.")
        return
    with st.container(border=True):
        sec("Claims")
        st.caption("Sample claims are pre-loaded — click **Open** to edit. Try IO16452 (in progress), "
                   "IO16454 (ready to lodge), or IO16456 (lodged — edit via post-lodgement change).")
        h = st.columns([1.1, 1.7, 1.5, 1.4, 1.2, 0.8])
        for col, t in zip(h, ["ACC45 NO.", "PATIENT", "ENCOUNTER", "ACCIDENT DATE", "STATUS", ""]):
            col.markdown(f'<div class="sec" style="margin:0">{t}</div>', unsafe_allow_html=True)
        for c in st.session_state.claims:
            cols = st.columns([1.1, 1.7, 1.5, 1.4, 1.2, 0.8])
            cols[0].markdown(f'<span class="mono" style="font-size:12.5px;color:var(--slate-700)">{c["reference"]}</span>', unsafe_allow_html=True)
            cols[1].write(f'{c["patient"]["given"]} {c["patient"]["family"]}')
            cols[2].markdown(f'<span class="mono">{c["encounter"]["external_id"]}</span>', unsafe_allow_html=True)
            cols[3].write(str(c["accident"]["adate"] or "—"))
            cols[4].markdown(status_pill(c["status"]), unsafe_allow_html=True)
            if cols[5].button("Open", key="open_" + c["id"]):
                st.session_state.active = c["id"]
                st.rerun()


def admin_panel(c):
    e, p, em, a = c["encounter"], c["patient"], c["employment"], c["accident"]
    with st.container(border=True):
        sec("Encounter context · from PAS/PMS")
        html('<div class="chips">'
             f'<span class="kv">Encounter <b>{e["external_id"]}</b></span>'
             f'<span class="kv">Source <b>{e["source_system"]}</b></span>'
             f'<span class="kv">Facility <b>{e["facility"]}</b></span>'
             f'<span class="kv">Provider <b>{e["provider"]}</b></span>'
             f'<span class="kv">ACC45 no. <b>{c["reference"]}</b> · '
             f'{"ACC allocation API" if c["number_source"]=="acc_allocation_api" else "pre-allocated block"}</span>'
             '</div>'
             '<div class="mono" style="color:var(--slate-400)">Identity inherited from the PMS — verify, don\'t re-key.</div>')

    col_l, col_r = st.columns(2)
    with col_l:
        with st.container(border=True):
            sec("Patient · ACC45 Part A")
            p["given"] = st.text_input("Given name *", value=p["given"])
            p["family"] = st.text_input("Family name *", value=p["family"])
            g1, g2 = st.columns(2)
            p["dob"] = g1.text_input("DOB * (YYYY-MM-DD)", value=p["dob"])
            p["nhi"] = g2.text_input("NHI", value=p["nhi"]).upper()
            g3, g4 = st.columns(2)
            p["mobile"] = g3.text_input("Mobile", value=p["mobile"])
            p["email"] = g4.text_input("Email", value=p["email"])
            p["address"] = st.text_input("Address", value=p["address"])
    with col_r:
        with st.container(border=True):
            sec("Employment · ACC45 Part B")
            em["status"] = st.selectbox("Employment status", EMP_STATUSES, index=EMP_STATUSES.index(em["status"]))
            em["occupation"] = st.text_input("Occupation", value=em["occupation"],
                                             disabled=em["status"] == "Not employed in NZ")
            em["employer"] = st.text_input("Employer", value=em["employer"], disabled=em["status"] != "Employee",
                                           placeholder="Required for employees" if em["status"] == "Employee" else "n/a")
        with st.container(border=True):
            sec("Patient consent · ACC45 Part E")
            if c["consent"]["given"]:
                html(f'<div class="bnr ok" style="margin:2px 0">✓ <b>Consent given</b> — {c["consent"]["at"]}. '
                     f'All three authorisations captured.</div>')
            else:
                st.caption("3-question script: (1) collect/use/disclose, (2) true & correct, (3) authorise lodgement.")
                if st.button("Record patient consent (all three = Yes)", type="primary"):
                    c["consent"] = {"given": True, "at": datetime.now().strftime("%d/%m/%Y %H:%M")}
                    st.rerun()

    with st.container(border=True):
        sec("Accident · ACC45 Part B")
        a1, a2, a3 = st.columns(3)
        a["adate"] = a1.date_input("Date of accident *", value=a["adate"] or date(2026, 7, 7))
        a["atime"] = a2.text_input("Time", value=a["atime"])
        a["location"] = a3.text_input("Location", value=a["location"])
        b1, b2, b3, b4 = st.columns(4)
        a["scene"] = b1.selectbox("Scene", SCENES, index=SCENES.index(a["scene"]))
        yn = ["No", "Yes"]
        a["workplace"] = b2.radio("Workplace?", yn, horizontal=True, index=yn.index(a["workplace"]))
        a["vehicle"] = b3.radio("Vehicle on road?", yn, horizontal=True, index=yn.index(a["vehicle"]))
        a["sporting"] = b4.radio("Sporting?", yn, horizontal=True, index=yn.index(a["sporting"]))
        a["cause"] = st.text_area("Cause of injury (mechanism) *", value=a["cause"], height=68,
                                  placeholder="e.g. walking to the kitchen – tripped over own feet – fell to ground")


def clinician_panel(c):
    role = st.session_state.role
    is_prescriber = role == "prescriber"
    locked = c["status"] not in ("draft", "ready")
    eligible = [d for d in c["diagnoses"] if d["acc"]]

    with st.container(border=True):
        sec("Context · from admin / encounter")
        consent_pill = '<span class="pill ok">recorded</span>' if c["consent"]["given"] else '<span class="pill err">missing</span>'
        html('<div class="chips">'
             f'<span class="kv">Patient <b>{c["patient"]["given"]} {c["patient"]["family"]}</b> ({c["patient"]["dob"]})</span>'
             f'<span class="kv">Accident <b>{c["accident"]["adate"] or "— not set"}</b></span>'
             f'<span class="kv">Scene <b>{c["accident"]["scene"]}</b></span>'
             f'<span class="kv">Consent {consent_pill}</span></div>'
             + (f'<div class="mono" style="color:var(--slate-400)">Cause: {c["accident"]["cause"]}</div>' if c["accident"]["cause"] else ""))

    with st.container(border=True):
        top = st.columns([3, 1.4])
        top[0].markdown('<div class="sec" style="margin-top:6px">Injury diagnosis &amp; assistance · ACC45 Part C</div>',
                        unsafe_allow_html=True)
        top[1].markdown(f'<div class="chips" style="justify-content:flex-end">'
                        f'<span class="pill blue">{len(c["diagnoses"])} dx · {len(eligible)} ACC-eligible</span></div>',
                        unsafe_allow_html=True)
        if not locked:
            if st.button("➕ Add diagnosis"):
                add_diagnosis_dialog(c)
        else:
            html('<span class="pill warn">Lodged — grid read-only; use Review tab to add a change</span>')

        if c["diagnoses"]:
            html(dx_table(c["diagnoses"]))
            if not locked:
                with st.expander("Edit diagnoses (remove)"):
                    for d in c["diagnoses"]:
                        r = st.columns([5, 1])
                        r[0].markdown(f'{d["display"]} <span class="mono">{d["code"]}</span>', unsafe_allow_html=True)
                        if r[1].button("Remove", key="del_" + d["id"]):
                            c["diagnoses"] = [x for x in c["diagnoses"] if x["id"] != d["id"]]
                            st.rerun()
        else:
            html('<div class="bnr err">✱ At least one injury diagnosis is needed.</div>')

        if c["diagnoses"] and not eligible:
            html('<div class="bnr err">⚠ <b>No ACC-eligible diagnosis yet.</b> Every diagnosis on this claim is '
                 'outside the ACC claim reference set. Add at least one ACC-eligible injury to lodge — this claim '
                 'cannot be submitted as-is.</div>')

    cflag, ccap = st.columns(2)
    with cflag:
        with st.container(border=True):
            sec("Clinical flags")
            f = c["flags"]
            yn = ["No", "Yes"]
            f["gradual"] = st.radio("Work-related gradual process?", yn, horizontal=True, index=yn.index(f["gradual"]))
            f["treatment"] = st.radio("Treatment injury?", yn, horizontal=True, index=yn.index(f["treatment"]))
            f["home"] = st.radio("Home assistance required?", yn, horizontal=True, index=yn.index(f["home"]))
            f["admitted"] = st.radio("Patient admitted?", yn, horizontal=True, index=yn.index(f["admitted"]))
            if f["treatment"] == "Yes":
                html('<div class="bnr warn">ℹ Treatment injury — ACC2152 + patient notes required before lodgement.</div>')
            if f["gradual"] == "Yes":
                html('<div class="bnr warn">ℹ Gradual process — medical practitioner only; work history needed.</div>')
    with ccap:
        with st.container(border=True):
            sec("Ability to work · Part D / ACC18")
            cap = c["capacity"]
            cap["exertion"] = st.selectbox("Normal work exertion", EXERTION, index=EXERTION.index(cap["exertion"]))
            states = ["", "Fully fit", "Fit for selected work", "Fully unfit"]
            cap["state"] = st.radio("Work capacity", states, horizontal=True, index=states.index(cap["state"]),
                                    format_func=lambda s: s or "—")
            if cap["state"] == "Fit for selected work":
                cap["restrictions"] = st.text_area("Restrictions / activities & type of work *", value=cap["restrictions"],
                                                   height=68, placeholder="e.g. seated duties, no lifting >5kg, max 4 hrs/day")
            if cap["state"] == "Fully unfit":
                cap["justification"] = st.text_area("Justification (return would risk health/safety) *",
                                                    value=cap["justification"], height=68)
            k1, k2 = st.columns([1.3, 1])
            cert_types = ["ACC45 initial (≤14 days)", "ACC18 (beyond 14 days)"]
            cap["cert_type"] = k1.selectbox("Certificate", cert_types, index=cert_types.index(cap["cert_type"]))
            cap["valid_from"] = k2.date_input("Valid from", value=cap["valid_from"] or date.today())
            cap["valid_to"] = k2.date_input("Valid to", value=cap["valid_to"] or date.today())
            if cap["state"] in ("Fit for selected work", "Fully unfit"):
                st.caption("With prior earnings, may enable weekly compensation (informational).")

    with st.container(border=True):
        sec("Practitioner declaration · ACC45 Part E")
        if not is_prescriber:
            html('<div class="bnr warn">🔒 <b>Part E is restricted to doctors and nurse practitioners.</b> '
                 'Switch role to a prescriber in the sidebar to sign, or route to an eligible colleague.</div>')
        st.caption("I certify I have personally examined the patient, the condition results from an accident, "
                   "and the patient authorised me to lodge this claim.")
        dec = c["declaration"]
        dcols = st.columns([1.4, 2])
        dec["provider_no"] = dcols[0].text_input("Provider number", value=dec["provider_no"],
                                                 placeholder="e.g. HP-44921", disabled=not is_prescriber)
        with dcols[1]:
            st.write("")
            if dec["made"]:
                html(f'<div class="bnr ok" style="margin-top:6px">✓ Declaration made {dec["date"]} by {dec["by"]}.</div>')
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
    with st.container(border=True):
        sec("Lodgement readiness")
        if not errs:
            html('<div class="bnr ok">✓ All mandatory requirements met — ready to lodge.</div>')
        else:
            html('<div class="bnr err"><b>Cannot lodge yet:</b><ul>'
                 + "".join(f"<li>{e}</li>" for e in errs) + "</ul></div>")
        if warns:
            html('<div class="bnr warn"><b>Warnings (non-blocking):</b><ul>'
                 + "".join(f"<li>{w}</li>" for w in warns) + "</ul></div>")

        if c["status"] in ("draft", "ready"):
            lc = st.columns([2, 3])
            if lc[0].button("Complete & lodge ACC45", type="primary", disabled=not can, use_container_width=True):
                for d in c["diagnoses"]:
                    d["status"] = "lodged"
                c["status"] = "lodged"
                c["decision"] = "Received"
                st.rerun()
            lc[1].caption("Validation passed." if can else "Complete is disabled until validation passes.")
            return

    # lodged view
    with st.container(border=True):
        html(f'<div class="bnr info">✓ ACC45 lodged. Decision: <b>{c["decision"]}</b>. Diagnosis grid is now '
             f'read-only; further clinical changes go through a diagnosis-change request.</div>')
        if c["status"] == "lodged":
            st.caption("Simulate ACC decision:")
            d1, d2, d3, _ = st.columns([1, 1, 1, 4])
            if d1.button("Accepted"):
                c["status"] = "accepted"; c["decision"] = "Accepted"; st.rerun()
            if d2.button("Held"):
                c["status"] = "held"; c["decision"] = "Held"; st.rerun()
            if d3.button("Declined"):
                c["status"] = "declined"; c["decision"] = "Declined"; st.rerun()

        sec("Diagnoses of record")
        html(dx_table(c["diagnoses"]))
        if st.button("➕ Add / change diagnosis (post-lodgement)", type="primary"):
            change_request_dialog(c)

        if c["change_requests"]:
            sec("Diagnosis change requests")
            rows = ""
            for r in c["change_requests"]:
                se = "✓" if r["same_event"] else "—"
                rows += (f'<tr><td>{r["kind"]}</td><td>{r["display"]} <span class="mono">{r["code"]}</span></td>'
                         f'<td>{se}</td><td>{r["bundled"]}</td><td><span class="pill warn">{r["status"]}</span></td></tr>')
            html('<table class="tbl"><thead><tr><th>Kind</th><th>Diagnosis</th><th>Same event</th>'
                 f'<th>Bundled</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>')


def workspace(c):
    errs, _, can = validate(c)
    hc = st.columns([1, 6])
    if hc[0].button("← Home", use_container_width=True):
        st.session_state.active = None
        st.rerun()
    html('<div class="apphdr"><span class="brand">🩺</span>'
         f'<span class="ref">{c["reference"]}</span>{status_pill(c["status"])}'
         f'<span class="sub">{c["patient"]["given"]} {c["patient"]["family"]} · '
         f'encounter {c["encounter"]["external_id"]} · accident {c["accident"]["adate"] or "—"}</span>'
         '<span class="grow"></span>'
         f'<span class="sub">{"✓ ready" if can else str(len(errs))+" to fix"}</span></div>')

    t_admin, t_clin, t_review = st.tabs(["📋 Administrative", "🩺 Clinician", "✅ Review & lodge"])
    with t_admin:
        admin_panel(c)
    with t_clin:
        clinician_panel(c)
    with t_review:
        review_panel(c)


# --------------------------------------------------------------------------
# sidebar (role) + router
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🩺 ACC Claim Console")
    st.caption("research mockup — stubbed ACC & terminology")
    st.divider()
    roles = {"prescriber": "Dr A. Rangi — GP (prescriber)",
             "limited": "J. Neho — Physiotherapist (limited)",
             "admin": "R. Patel — Reception (admin)"}
    st.session_state.role = st.radio("Signed in as", list(roles.keys()),
                                     format_func=lambda r: roles[r],
                                     index=list(roles).index(st.session_state.role))
    st.divider()
    st.caption("Try: switch to the physiotherapist to see Part E lock; add only a non-eligible code (e.g. "
               "“Anxiety disorder”) to see the lodge block.")

c = active_claim()
if c is None:
    dashboard()
else:
    workspace(c)
