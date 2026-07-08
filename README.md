# ACC Claim Console — Streamlit mockup

A two-role console for lodging New Zealand ACC injury claims (**ACC45**) and medical
certificates (**ACC18**), built as an interactive **Streamlit** mockup for demo and
product-validation purposes.

> **Mockup only.** ACC lodgement and SNOMED CT terminology are **stubbed** — nothing is
> sent to ACC, and the diagnosis picker uses a small in-file sample of the
> `acc-claim-reference-set` value set. No real patient data. Not for clinical use.

## What it demonstrates

- **Encounter-context launch** — a new claim simulates a PAS/PMS (Medtech) encounter,
  inherits the patient, and allocates a fresh ACC45 number.
- **Administrative interface** — ACC45 Part A/B (patient, employment, accident) plus the
  three-question patient consent capture.
- **Clinician interface** — the diagnosis grid with **ACC-eligibility feedback at entry**
  (each SNOMED concept is flagged ACC-eligible / not eligible), clinical flags, work-capacity
  certification (ACC45 initial vs ACC18), and a **role-gated Part E declaration**.
- **Hard eligibility gate** — *Complete & lodge* is disabled until validation passes,
  including **at least one ACC-eligible diagnosis**.
- **Post-lodgement change** — after lodging, the grid is read-only and adding a diagnosis
  goes through a **Change-in-Diagnosis request** with a same-event confirmation and an
  "attach to ACC18" option.

Use the **sidebar role switcher** to see Part E lock for a limited-scope provider.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501.

## Deploy on Streamlit Community Cloud (free, from GitHub)

1. Push this folder to a GitHub repo (see below).
2. Go to <https://share.streamlit.io> and sign in with GitHub.
3. **Create app** → **Deploy a public app from GitHub**.
4. Pick your repo, set **Branch** to `main`, set **Main file path** to `app.py`, click **Deploy**.

Streamlit installs `requirements.txt` automatically and gives you a public
`https://<app>.streamlit.app` URL. Pushes to the branch redeploy automatically.

## Push to GitHub

```bash
cd acc-claim-console
git init
git add .
git commit -m "ACC Claim Console — Streamlit mockup"
git branch -M main
git remote add origin https://github.com/<you>/acc-claim-console.git
git push -u origin main
```

(Create the empty `acc-claim-console` repo on GitHub first, then run the above.)

## Files

| File | Purpose |
|---|---|
| `app.py` | The whole app (single file). |
| `connectors.py` | External integration seams (auth, NHI, HPI, PMS, terminology, ACC, audit, persistence, notifications) — all **stubbed**. |
| `requirements.txt` | `streamlit>=1.37` (needs `st.dialog`). |
| `.streamlit/config.toml` | Theme + headless server. |
| `.gitignore` | Excludes venv, caches, secrets. |
| `AS-BUILT-SPEC.md` | Build-agnostic spec to replicate the app on any stack. |
| `PRODUCTION-READINESS.md` | Gap analysis for deploying into the Health NZ ecosystem. |

## Notes for turning this into a real product

- Replace the stubbed `TERM` list with live `$expand` / `$validate-code` calls against a
  SNOMED CT NZ Edition terminology server; keep the ACC-eligibility flag bound to the
  `acc-claim-reference-set` value set.
- Replace the simulated encounter + ACC number allocation with real PAS/PMS launch context
  and ACC's Claim Number Allocation API.
- `st.session_state` holds all state in memory per session; a real build needs a persistence
  layer and an audit trail. See the accompanying product & FHIR specifications.
