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
from datetime import date, datetime, timedelta

EDIT_WINDOW_DAYS = 14  # ACC45 referrals are retained for update/revision/repair for 14 days

import streamlit as st

import connectors as cx  # external integration seams (all stubbed) — see PRODUCTION-READINESS.md

st.set_page_config(page_title="ACC Claim Console", page_icon="🩺", layout="wide")

# --------------------------------------------------------------------------
# SNOMED CT terminology (the ACC claim reference set) is provided by the
# terminology connector (connectors.terminology) — a stub of the NZHTS value set.
# --------------------------------------------------------------------------

EMP_STATUSES = ["Not employed in NZ", "Retired", "Employee", "Self-employed", "Owner employee", "Other"]
SCENES = ["Home", "Work", "Road", "Sports facility", "School", "Other"]
EXERTION = ["", "Sedentary", "Light", "Medium", "Heavy", "Very heavy"]

# --------------------------------------------------------------------------
# Health New Zealand | Te Whatu Ora design system (scoped, injected once).
# Palette + Fira Sans per the HNZ digital identity brand guidelines:
#   navy #252A47 · deep blue #002E6E (primary) · mid blue #7EB6DC (focus)
#   light blue #EEF4FA · teal #A7DEE1 / #D3EFF0.
# Variable names retain the slate/blue/... scale so component styles are stable;
# their VALUES are the HNZ brand colours.
# --------------------------------------------------------------------------
CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Fira+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap');
  :root{
    /* HNZ brand */
    --navy:#252A47; --blue:#002E6E; --blue-mid:#7EB6DC; --teal:#A7DEE1; --teal-50:#D3EFF0;
    /* neutral scale, tinted toward HNZ navy */
    --slate-50:#F4F8FC; --slate-100:#EDF2F8; --slate-200:#D8E3EF; --slate-300:#C3D2E2;
    --slate-400:#8398B0; --slate-500:#566579; --slate-600:#3E4C60; --slate-700:#2B3850;
    --slate-800:#252A47; --slate-900:#1A1F36;
    /* brand blue mapped onto the blue-* names used across components */
    --blue-50:#EEF4FA; --blue-100:#DCEAF6; --blue-200:#BBD3EC;
    --blue-600:#002E6E; --blue-700:#002454; --blue-800:#002E6E;
    /* semantic */
    --green-50:#E7F4EC; --green-200:#B7E0C7; --green-600:#1F8A54; --green-700:#17663E;
    --amber-50:#FFF6E5; --amber-200:#F6DCA1; --amber-600:#B4791A; --amber-700:#8A5A00;
    --red-50:#FBEBEA; --red-200:#F3C3BF; --red-600:#C0362C; --red-700:#8F2A22;
  }
  html, body, [class*="css"], .stMarkdown, p, span, div, label, input, textarea, select, button{
    font-family:'Fira Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size:13px;
  }
  .stApp{background:#fff;}
  /* keep content clear of Streamlit's fixed top header */
  [data-testid="stHeader"]{background:rgba(255,255,255,.85); backdrop-filter:blur(4px);}
  .block-container{padding-top:4rem !important; padding-bottom:2.5rem !important; max-width:1180px;}
  [data-testid="stVerticalBlock"]{gap:.5rem;}
  [data-testid="stHorizontalBlock"]{gap:.55rem;}
  [data-testid="stElementContainer"]{margin-bottom:0 !important;}
  hr{margin:.5rem 0 !important; border-color:var(--slate-200);}
  h1,h2,h3,h4{letter-spacing:-.01em; color:var(--navy); font-weight:700;}

  /* cards = bordered containers */
  [data-testid="stVerticalBlockBorderWrapper"]{
    background:#fff; border:1px solid var(--slate-200) !important; border-radius:12px;
    box-shadow:0 1px 2px rgba(37,42,71,.06); padding:2px 4px;
  }

  /* buttons */
  .stButton>button{
    border-radius:8px; border:1px solid var(--slate-300); background:#fff; color:var(--blue);
    padding:.34rem .8rem; font-weight:600; font-size:12.5px; transition:all .12s;
  }
  .stButton>button:hover{border-color:var(--blue-mid); background:var(--blue-50);}
  .stButton>button[kind="primary"]{background:var(--blue); border-color:var(--blue); color:#fff;}
  .stButton>button[kind="primary"]:hover{background:var(--blue-700); border-color:var(--blue-700);}
  .stButton>button:focus-visible{outline:3px solid var(--blue-mid); outline-offset:1px;}
  .stButton>button:disabled{background:var(--slate-100); color:var(--slate-400); border-color:var(--slate-200);}

  /* inputs — compact, HNZ focus ring */
  .stTextInput input, .stDateInput input, .stNumberInput input{padding:.32rem .55rem !important; font-size:12.5px;}
  .stTextArea textarea{padding:.4rem .55rem !important; font-size:12.5px;}
  div[data-baseweb="select"]>div{min-height:34px; font-size:12.5px;}
  .stTextInput input:focus, .stDateInput input:focus, .stTextArea textarea:focus{
    border-color:var(--blue-mid) !important; box-shadow:0 0 0 3px rgba(126,182,220,.35) !important;}
  label p{font-size:11.5px !important; color:var(--slate-600) !important; font-weight:600 !important; margin-bottom:2px !important;}
  [data-testid="stWidgetLabel"]{margin-bottom:1px;}

  /* radio horizontal → segmented look */
  [role="radiogroup"]{gap:.4rem;}
  [role="radiogroup"] label{background:#fff; border:1px solid var(--slate-200); border-radius:7px; padding:2px 9px;}

  /* Tabs are built from st.buttons in workspace() (a custom nav bar) rather than
     st.tabs — avoids fragile baseweb internals and stays readable on every version.
     Active tab = primary (blue/white); inactive = secondary (white/blue). Both readable. */

  /* sidebar — HNZ navy */
  [data-testid="stSidebar"]{background:var(--navy);}
  [data-testid="stSidebar"] *{color:#EAF0F7 !important;}
  [data-testid="stSidebar"] [role="radiogroup"] label{background:rgba(255,255,255,.06); border-color:rgba(255,255,255,.14);}

  /* --- utility components --- */
  .apphdr{display:flex; align-items:center; gap:12px; padding:12px 16px; margin-bottom:10px;
    background:linear-gradient(90deg,var(--navy),var(--blue)); border-radius:12px; color:#fff;}
  .apphdr .brand{font-weight:700; letter-spacing:.2px; font-size:15px;}
  .apphdr .ref{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; background:rgba(255,255,255,.14);
    padding:2px 9px; border-radius:7px; font-size:12.5px;}
  .apphdr .sub{color:#C7D3E5; font-size:12px;}
  .apphdr .grow{flex:1;}

  .sec{font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:var(--blue);
    font-weight:700; margin:2px 0 6px;}
  .chips{display:flex; flex-wrap:wrap; gap:6px; margin:2px 0 6px;}
  .kv{background:var(--slate-50); border:1px solid var(--slate-200); border-radius:8px; padding:3px 9px;
    font-size:11.5px; color:var(--slate-500);}
  .kv b{color:var(--navy); font-weight:700;}
  .mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11px; color:var(--slate-400);}

  .pill{display:inline-block; padding:1px 8px; border-radius:999px; font-size:10.5px; font-weight:700;
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
    border-bottom:1px solid var(--slate-200); font-size:10px; text-transform:uppercase; letter-spacing:.05em; font-weight:700;}
  table.tbl td{padding:6px 10px; border-bottom:1px solid var(--slate-100); color:var(--slate-700); vertical-align:middle;}
  table.tbl tr:last-child td{border-bottom:0;}

  /* definition grid for the claim summary */
  .dlgrid{display:grid; grid-template-columns:1fr 1fr; gap:0 22px; margin:2px 0 6px;}
  .dl{display:flex; gap:10px; padding:4px 0; border-bottom:1px solid var(--slate-100);}
  .dt{color:var(--slate-500); font-size:11.5px; min-width:132px; font-weight:600; flex:none;}
  .dd{color:var(--navy); font-size:12.5px; font-weight:600;}
  @media(max-width:700px){.dlgrid{grid-template-columns:1fr;}}

  /* dashboard summary metric cards */
  .metricrow{display:flex; gap:8px; flex-wrap:wrap; margin:2px 0 6px;}
  .metric{flex:1 1 120px; border:1px solid var(--slate-200); border-radius:10px; padding:8px 12px; background:#fff;}
  .metric .mv{font-size:22px; font-weight:700; color:var(--navy); line-height:1.05;}
  .metric .ml{font-size:10px; color:var(--slate-500); text-transform:uppercase; letter-spacing:.04em; font-weight:700; margin-top:3px;}
  .metric.warn{background:var(--amber-50); border-color:var(--amber-200);} .metric.warn .mv{color:var(--amber-700);}
  .metric.err{background:var(--red-50); border-color:var(--red-200);} .metric.err .mv{color:var(--red-700);}
</style>
"""


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def uid():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=7))


def allocate_number():
    # ACC Claim Number Allocation API (stubbed via connectors.acc)
    n = cx.acc.allocate_claim_number(st.session_state.seq)
    st.session_state.seq += 1
    return n


def new_claim():
    ctx = cx.pms.get_encounter_context()  # PMS/PAS launch context (stubbed)
    return {
        "id": uid(),
        "reference": allocate_number(),
        "number_source": "acc_allocation_api",
        "status": "draft",
        "decision": None,
        "created": date.today(),
        "created_by": cx.auth.current_user(st.session_state.get("role", "prescriber"))["name"],
        "encounter": ctx["encounter"],
        "patient": ctx["patient"],
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
    elif not cx.nhi.validate(p["nhi"]):
        warns.append("NHI format looks invalid (real check-character validation is via the NHI service).")
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


# ----- 14-day edit/revision/repair window --------------------------------
def days_left(c):
    """Days remaining in the 14-day update/revision/repair window."""
    created = c.get("created") or date.today()
    return EDIT_WINDOW_DAYS - (date.today() - created).days


def is_expired(c):
    return days_left(c) <= 0


def window_pill(c):
    d = days_left(c)
    if d <= 0:
        return '<span class="pill err">Edit window expired</span>'
    cls = "err" if d <= 3 else ("warn" if d <= 7 else "blue")
    unit = "day" if d == 1 else "days"
    return f'<span class="pill {cls}">{d} {unit} left to edit</span>'


def needs_repair(c):
    """Referral the user should act on: unfinished draft, or an ACC decision to address."""
    return c["status"] in ("draft", "held", "declined")


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
        "created": date.today(), "created_by": "Dr A. Rangi",
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
        "status": "draft", "created": date.today() - timedelta(days=3),
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
        "status": "ready", "created": date.today() - timedelta(days=1),
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
        "status": "accepted", "decision": "Accepted", "created": date.today() - timedelta(days=9),
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
    # 4) DECLINED — needs repair and the edit window is closing (2 days left).
    c4 = _merge(_base("IO16450"), {
        "status": "declined", "decision": "Declined", "created": date.today() - timedelta(days=12),
        "patient": {"pas_id": "PAS-33902", "given": "Tomasi", "family": "Vaka", "dob": "1988-09-14",
                    "nhi": "PLR5521", "mobile": "021 700 4412", "address": "88 Rata Street, Christchurch 8011"},
        "employment": {"status": "Employee", "occupation": "Courier driver", "employer": "FastParcel NZ"},
        "accident": {"adate": date.today() - timedelta(days=12), "atime": "07:50", "location": "Christchurch City",
                     "scene": "Road", "vehicle": "Yes", "cause": "rear-ended at traffic lights – neck pain"},
        "consent": {"given": True, "at": "(recorded)"},
        "diagnoses": [_dx("44465007", "Sprain of neck", "N/A", True, "declined", True)],
        "declaration": {"made": True, "date": "(signed)", "by": "Dr A. Rangi", "provider_no": "HP-44921"},
    })
    # 5) EXPIRED — outside the 14-day window; read-only / archived (16 days old).
    c5 = _merge(_base("IO16445"), {
        "status": "accepted", "decision": "Accepted", "created": date.today() - timedelta(days=16),
        "patient": {"pas_id": "PAS-21847", "given": "Grace", "family": "Wilson", "dob": "1962-01-30",
                    "nhi": "QDF3390", "mobile": "027 118 2244", "address": "3 Miro Place, Christchurch 8042"},
        "employment": {"status": "Retired", "occupation": "", "employer": ""},
        "accident": {"adate": date.today() - timedelta(days=16), "atime": "11:15", "location": "Christchurch City",
                     "scene": "Home", "cause": "tripped on a rug – landed on right wrist"},
        "consent": {"given": True, "at": "(recorded)"},
        "diagnoses": [_dx("20946005", "Fracture of distal radius (wrist)", "Right", True, "accepted", True)],
        "declaration": {"made": True, "date": "(signed)", "by": "Dr A. Rangi", "provider_no": "HP-44921"},
    })
    return [c2, c1, c4, c3, c5]


# --------------------------------------------------------------------------
# session state init
# --------------------------------------------------------------------------
if "claims" not in st.session_state:
    st.session_state.seq = 16457          # new claims continue after the seeded refs
    st.session_state.claims = seed_claims()
    st.session_state.active = None
    st.session_state.role = "prescriber"
    st.session_state.tab = "admin"        # active workspace tab

st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# dialogs
# --------------------------------------------------------------------------
@st.dialog("Add diagnosis")
def add_diagnosis_dialog(c):
    scoped = st.checkbox("Scope to ACC-claimable concepts", value=True)
    q = st.text_input("Search SNOMED CT", placeholder="e.g. sprain, wrist, laceration, knee")
    pool = cx.terminology.search(q, eligible_only=scoped)  # FHIR $expand (stub)
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
    pool = cx.terminology.search(q, eligible_only=False)  # FHIR $expand (stub)
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
        cx.audit.record(st.session_state.role, "diagnosis_change_request", f'{c["reference"]}: +{sel["code"]}')
        st.rerun()


# --------------------------------------------------------------------------
# panels
# --------------------------------------------------------------------------
def _submission_row(c, read_only=False):
    cols = st.columns([1.05, 1.7, 1.35, 1.15, 1.6, 0.75])
    cols[0].markdown(f'<span class="mono" style="font-size:12.5px;color:var(--slate-700)">{c["reference"]}</span>',
                     unsafe_allow_html=True)
    repair = ' <span class="pill warn">needs action</span>' if (needs_repair(c) and not read_only) else ""
    cols[1].markdown(f'{c["patient"]["given"]} {c["patient"]["family"]}{repair}', unsafe_allow_html=True)
    cols[2].markdown(status_pill(c["status"]), unsafe_allow_html=True)
    cols[3].write(str(c["accident"]["adate"] or "—"))
    cols[4].markdown(window_pill(c), unsafe_allow_html=True)
    if cols[5].button("Open" if not read_only else "View", key="open_" + c["id"]):
        st.session_state.active = c["id"]
        st.session_state.tab = "admin"
        st.rerun()


def dashboard():
    user = cx.auth.current_user(st.session_state.get("role", "prescriber"))
    html('<div class="apphdr">'
         '<span class="brand">Health New Zealand <span style="font-weight:400;opacity:.75">| Te Whatu Ora</span></span>'
         '<span class="sub">ACC Claim Console · research mockup</span><span class="grow"></span>'
         f'<span class="sub">{user["name"]} · {user["role_label"]}</span></div>')

    # per-user working set
    mine = [c for c in st.session_state.claims if c.get("created_by") == user["name"]]
    active = sorted([c for c in mine if not is_expired(c)], key=days_left)
    expired = sorted([c for c in mine if is_expired(c)], key=lambda c: c.get("created") or date.today())

    st.markdown("#### My ACC submissions")
    st.caption("ACC45 referrals are kept here for **14 days** for update, revision or repair. "
               "After that they drop off your active list (read-only below).")

    # summary metrics over the active working set
    drafts = sum(1 for c in active if c["status"] == "draft")
    ready = sum(1 for c in active if c["status"] == "ready")
    awaiting = sum(1 for c in active if c["status"] == "lodged")
    repair = sum(1 for c in active if c["status"] in ("held", "declined"))
    expiring = sum(1 for c in active if 0 < days_left(c) <= 3)
    html('<div class="metricrow">'
         f'<div class="metric"><div class="mv">{len(active)}</div><div class="ml">Active</div></div>'
         f'<div class="metric"><div class="mv">{drafts}</div><div class="ml">Drafts to finish</div></div>'
         f'<div class="metric"><div class="mv">{ready}</div><div class="ml">Ready to lodge</div></div>'
         f'<div class="metric"><div class="mv">{awaiting}</div><div class="ml">Awaiting ACC</div></div>'
         f'<div class="metric{" err" if repair else ""}"><div class="mv">{repair}</div><div class="ml">Needs repair</div></div>'
         f'<div class="metric{" warn" if expiring else ""}"><div class="mv">{expiring}</div><div class="ml">Expiring ≤3 days</div></div>'
         '</div>')

    if st.button("➕ New ACC45 claim (from PMS encounter)", type="primary"):
        c = new_claim()
        st.session_state.claims.append(c)
        st.session_state.active = c["id"]
        st.session_state.tab = "admin"
        st.rerun()

    # active submissions (inside the 14-day window), most urgent first
    with st.container(border=True):
        sec("Active submissions · within 14-day edit window")
        if not active:
            st.caption(f"No active submissions for {user['name']}.")
        else:
            h = st.columns([1.05, 1.7, 1.35, 1.15, 1.6, 0.75])
            for col, t in zip(h, ["ACC45 NO.", "PATIENT", "STATUS", "ACCIDENT", "EDIT WINDOW", ""]):
                col.markdown(f'<div class="sec" style="margin:0">{t}</div>', unsafe_allow_html=True)
            for c in active:
                _submission_row(c)

    # expired / archived — read-only
    if expired:
        with st.expander(f"Expired — read-only (past 14-day window) · {len(expired)}"):
            st.caption("The 14-day update/revision/repair window has closed. These are shown for reference only.")
            for c in expired:
                _submission_row(c, read_only=True)


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
            if p["nhi"]:
                if cx.nhi.validate(p["nhi"]):
                    html('<span class="pill ok">NHI format valid</span> '
                         '<span class="mono" style="color:var(--slate-400)">check-digit &amp; demographics via NHI service (stub)</span>')
                else:
                    html('<span class="pill err">NHI format invalid</span>')
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
                    cx.audit.record(st.session_state.role, "consent_recorded", c["reference"])
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
    is_prescriber = cx.auth.can_sign_part_e(role)  # authorisation via auth connector (stub)
    locked = c["status"] not in ("draft", "ready") or is_expired(c)
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
                    dec["by"] = cx.auth.current_user(st.session_state.role)["name"]
                    if not dec["provider_no"]:
                        dec["provider_no"] = cx.hpi.default_provider_number()
                    cx.audit.record(st.session_state.role, "part_e_declaration", c["reference"])
                    st.rerun()


def render_summary(c):
    """Full ACC45 summary of everything entered on the form."""
    p, e, a, cap, dec, fl = (c["patient"], c["employment"], c["accident"],
                             c["capacity"], c["declaration"], c["flags"])

    def dl(pairs):
        return ('<div class="dlgrid">' + "".join(
            f'<div class="dl"><span class="dt">{k}</span>'
            f'<span class="dd">{v if v not in (None, "", "None") else "—"}</span></div>'
            for k, v in pairs) + '</div>')

    def wide(k, v):
        return f'<div class="dl" style="border:0"><span class="dt">{k}</span><span class="dd">{v or "—"}</span></div>'

    with st.container(border=True):
        sec("Claim summary · ACC45")
        html(dl([
            ("ACC45 number", c["reference"]),
            ("Status", STATUS.get(c["status"], ("", c["status"]))[1]),
            ("Encounter", c["encounter"]["external_id"]),
            ("Source system", c["encounter"]["source_system"]),
            ("Facility", c["encounter"]["facility"]),
            ("Attending provider", c["encounter"]["provider"]),
        ]))

        sec("Patient · Part A")
        html(dl([
            ("Name", f'{p["given"]} {p["family"]}'.strip()),
            ("Date of birth", p["dob"]),
            ("NHI", p["nhi"]),
            ("Mobile", p["mobile"]),
            ("Email", p["email"]),
            ("Address", p["address"]),
        ]))

        sec("Employment · Part B")
        html(dl([("Employment status", e["status"]), ("Occupation", e["occupation"]),
                 ("Employer", e["employer"])]))

        sec("Accident · Part B")
        html(dl([
            ("Date / time", f'{a["adate"] or "—"} {a["atime"]}'.strip()),
            ("Location", a["location"]),
            ("Scene", a["scene"]),
            ("Workplace accident", a["workplace"]),
            ("Moving vehicle on road", a["vehicle"]),
            ("Sporting injury", a["sporting"]),
        ]))
        html(wide("Cause of injury", a["cause"]))

        sec("Consent · Part E (patient)")
        if c["consent"]["given"]:
            html(f'<span class="pill ok">Consent recorded</span> &nbsp;'
                 f'<span class="kv">Given {c["consent"]["at"]} · all three authorisations</span>')
        else:
            html('<span class="pill err">Consent not recorded</span>')

        sec("Diagnoses · Part C")
        if c["diagnoses"]:
            html(dx_table(c["diagnoses"]))
        else:
            html('<span class="pill err">No diagnoses entered</span>')
        html('<div class="chips">'
             f'<span class="kv">Gradual process <b>{fl["gradual"]}</b></span>'
             f'<span class="kv">Treatment injury <b>{fl["treatment"]}</b></span>'
             f'<span class="kv">Admitted <b>{fl["admitted"]}</b></span>'
             f'<span class="kv">Home assistance <b>{fl["home"]}</b></span></div>')

        sec("Ability to work · Part D / ACC18")
        html(dl([
            ("Normal work exertion", cap["exertion"]),
            ("Work capacity", cap["state"]),
            ("Certificate", cap["cert_type"]),
            ("Valid", f'{cap["valid_from"] or "—"} → {cap["valid_to"] or "—"}'),
        ]))
        restr = cap["restrictions"] or cap["justification"]
        if restr:
            html(wide("Restrictions / justification", restr))

        sec("Practitioner declaration · Part E")
        if dec["made"]:
            html(f'<span class="pill ok">Declaration made</span> &nbsp;'
                 f'<span class="kv">{dec["date"]} · {dec["by"]} · provider {dec["provider_no"]}</span>')
        else:
            html('<span class="pill err">Declaration not completed</span>')


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
            expired = is_expired(c)
            lc = st.columns([2, 3])
            if lc[0].button("Complete & lodge ACC45", type="primary", disabled=(not can or expired), use_container_width=True):
                for d in c["diagnoses"]:
                    d["status"] = "lodged"
                c["status"] = "lodged"
                c["decision"] = cx.acc.lodge(c)  # ACC eLodgement (stub)
                cx.audit.record(st.session_state.role, "lodge_acc45", c["reference"])
                cx.notification.send_decision_sms(c["patient"]["mobile"], c["reference"], c["decision"])
                st.rerun()
            lc[1].caption("Edit window expired — cannot lodge." if expired
                          else ("Validation passed." if can else "Complete is disabled until validation passes."))

    # Full ACC45 summary — directly under Lodgement readiness, for every claim state.
    render_summary(c)

    # Post-lodgement actions (only once the claim has been lodged).
    if c["status"] not in ("draft", "ready"):
        with st.container(border=True):
            html(f'<div class="bnr info">✓ ACC45 lodged. Decision: <b>{c["decision"]}</b>. Diagnosis grid is now '
                 f'read-only; further clinical changes go through a diagnosis-change request.</div>')
            if c["status"] == "lodged":
                st.caption("Simulate ACC decision:")
                d1, d2, d3, _ = st.columns([1, 1, 1, 4])
                if d1.button("Accepted"):
                    c["status"] = "accepted"; c["decision"] = cx.acc.decision("Accepted")
                    cx.audit.record(st.session_state.role, "acc_decision", f'{c["reference"]}: Accepted'); st.rerun()
                if d2.button("Held"):
                    c["status"] = "held"; c["decision"] = cx.acc.decision("Held")
                    cx.audit.record(st.session_state.role, "acc_decision", f'{c["reference"]}: Held'); st.rerun()
                if d3.button("Declined"):
                    c["status"] = "declined"; c["decision"] = cx.acc.decision("Declined")
                    cx.audit.record(st.session_state.role, "acc_decision", f'{c["reference"]}: Declined'); st.rerun()

            sec("Post-lodgement diagnosis changes")
            if st.button("➕ Add / change diagnosis (post-lodgement)", type="primary"):
                change_request_dialog(c)

            if c["change_requests"]:
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
    html('<div class="apphdr"><span class="brand" style="font-size:13px">Health NZ</span>'
         f'<span class="ref">{c["reference"]}</span>{status_pill(c["status"])} {window_pill(c)}'
         f'<span class="sub">{c["patient"]["given"]} {c["patient"]["family"]} · '
         f'encounter {c["encounter"]["external_id"]} · accident {c["accident"]["adate"] or "—"}</span>'
         '<span class="grow"></span>'
         f'<span class="sub">{"✓ ready" if can else str(len(errs))+" to fix"}</span></div>')
    if is_expired(c):
        html('<div class="bnr err">🔒 <b>Read-only — the 14-day update/revision/repair window has closed.</b> '
             'This referral can no longer be edited or lodged. (Ongoing certification would continue via a new ACC18.)</div>')

    # Custom tab bar (buttons) — reliable & readable across Streamlit versions.
    tabs = [("admin", "📋  Administrative"), ("clin", "🩺  Clinician"),
            ("review", "✅  Review & lodge")]
    with st.container(border=True):
        ncols = st.columns(len(tabs))
        for i, (key, label) in enumerate(tabs):
            is_active = st.session_state.get("tab", "admin") == key
            if ncols[i].button(label, key="nav_" + key, use_container_width=True,
                               type="primary" if is_active else "secondary"):
                st.session_state.tab = key
                st.rerun()
    active = st.session_state.get("tab", "admin")
    if active == "admin":
        admin_panel(c)
    elif active == "clin":
        clinician_panel(c)
    else:
        review_panel(c)


# --------------------------------------------------------------------------
# sidebar (role) + router
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ACC Claim Console")
    st.caption("Health New Zealand | Te Whatu Ora · research mockup")
    st.divider()
    roles = {"prescriber": "Dr A. Rangi — GP (prescriber)",
             "limited": "J. Neho — Physiotherapist (limited)",
             "admin": "R. Patel — Reception (admin)"}
    st.session_state.role = st.radio("Signed in as", list(roles.keys()),
                                     format_func=lambda r: roles[r],
                                     index=list(roles).index(st.session_state.role))
    st.caption("🔒 Sign-in is **simulated** (dev only). Production uses My Health Account "
               "Workforce (OIDC) via the auth connector.")
    st.divider()
    st.caption("Try: switch to the physiotherapist to see Part E lock; add only a non-eligible code (e.g. "
               "“Anxiety disorder”) to see the lodge block.")
    with st.expander("Integration status (stubbed connectors)"):
        for name, mode in cx.CONNECTOR_MODE.items():
            st.caption(f"• {name} — {mode}")

c = active_claim()
if c is None:
    dashboard()
else:
    workspace(c)
