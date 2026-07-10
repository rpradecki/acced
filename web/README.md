# ACC Claim Console — Next.js build

The ACC45 / ACC18 console as a plain web app: **Next.js (App Router) + TypeScript**, no UI
framework, hand-written CSS implementing the Health NZ | Te Whatu Ora design system.

This is a port of the Streamlit mockup in the repo root. The domain logic is identical; the
UI owns its own DOM.

> **Mockup only.** ACC lodgement and SNOMED CT terminology are **stubbed**. No real patient
> data. Not for clinical use.

## Why this exists

The Streamlit build hand-wrote every visual element as raw HTML/CSS injected through
`st.markdown`, then fought Streamlit's generated DOM to make it render:

- a stray `None` painted on every page (Streamlit "magic" renders root-level expressions);
- card styling silently dead — `[data-testid="stVerticalBlockBorderWrapper"]` matches nothing
  in current Streamlit;
- column-header text overlapping the row beneath, because Streamlit wraps injected block HTML
  in a flex box that collapsed it to ~4.6px;
- emotion-hash class names and `st-key-*` containers needed as stable CSS hooks.

None of those failure modes exist here. `.claimrow` uses one CSS grid template shared by the
header and the data rows, so **columns cannot drift or overlap** — it is structural, not a
min-height workaround. Spacing is a single `--gap` token.

The app is also a **forms/CRUD app**, which is Streamlit's weakest category and the web
platform's strongest. And the spec's accessibility bar (WCAG 2.1 AA, keyboard-first diagnosis
entry) needs DOM control that Streamlit does not give.

## Run locally

```bash
npm install
npm run dev     # http://localhost:3000
npm run build   # production build
```

## Deploy on Vercel

1. Import the GitHub repo at <https://vercel.com/new>.
2. Set **Root Directory** to `web` — the Next.js app is not at the repo root.
3. Framework preset auto-detects as **Next.js**. No env vars needed (everything is stubbed).
4. Deploy. Pushes to `main` redeploy automatically; PRs get preview deployments.

### Hosting does not equal compliance

`PRODUCTION-READINESS.md` §G requires **NZ data residency** and nods to Māori Data
Sovereignty (Te Mana Raraunga). **Vercel has no New Zealand region** (nearest is Sydney), and
Streamlit Community Cloud is US-hosted. Neither satisfies that bar.

That is fine for a research mockup with synthetic patients — but moving to Vercel is a
developer-experience and UI-control decision, **not** progress toward production compliance.
A real deployment lands on an NZ-region host regardless of framework.

## Architecture

The **connector seams are preserved** from the Python build — every external boundary is one
stubbed module, documented with the real Health NZ service it stands in for. Going live means
implementing the real client inside a connector; the UI should not change.

| Path | Purpose |
|---|---|
| `lib/types.ts` | The claim aggregate (mirrors `DATABASE-SCHEMA.md`). |
| `lib/domain.ts` | Pure rules: `validate`, `readiness`, the 14-day / 12-month windows. No framework imports. |
| `lib/connectors.ts` | auth · NHI · HPI · PMS · SDHR · terminology · ACC · audit · persistence · notification — all **stubbed**. |
| `lib/seed.ts` | Sample claims + a synthesised attributed audit trail. |
| `lib/store.tsx` | React context replacing `st.session_state`, incl. the per-identity working set. |
| `components/` | Dashboard, workspace (admin/clinician/review), dialogs, audit views. |
| `app/globals.css` | The HNZ design system. |

## Known gaps vs. production

- **State is in memory** — a page reload reseeds. Production swaps `lib/store.tsx` for the
  persistence connector against an NZ-region datastore.
- **No optimistic locking.** Drafts are shared-editable; production must reject a save when
  another author has saved since the editor loaded the claim. See `PRODUCTION-READINESS.md` §G.
- **No facility scoping.** Single-practice prototype; production needs row-level security
  keyed on the facility (HPI Organisation) plus break-glass. See §A.
- **Auth is a dev-only role switcher.** Production uses My Health Account Workforce (OIDC).
