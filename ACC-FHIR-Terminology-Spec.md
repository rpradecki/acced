# ACC Claim Reference Set — FHIR Terminology Specification

Companion to the ACC Claim Lodgement product spec. Documents the FHIR terminology
artifact that binds the clinician diagnosis picker and drives the "ACC?" eligibility flag.
Captured live from the NZ Health Terminology Service (NZHTS) on 8 July 2026.

---

## 1. The resource

`ValueSet` (FHIR R4), retrieved from:

```
GET https://nzhts.digital.health.nz/fhir/ValueSet/acc-claim-reference-set
Accept: application/fhir+json
```

> Note: the endpoint serves **gzip-encoded** `application/fhir+json`. A naive HTTP
> client that doesn't handle `Content-Encoding: gzip` receives binary. Use a browser/
> client that decodes gzip, or pass `Accept-Encoding: identity`.

### Resource metadata (as published)

| Element | Value |
|---|---|
| `resourceType` | `ValueSet` |
| `id` | `acc-claim-reference-set` |
| `url` | `https://nzhts.digital.health.nz/fhir/ValueSet/acc-claim-reference-set` |
| `version` | `20260401` (date-style version; the value set is versioned — pin it) |
| `name` | `Acc_claim_reference_set` |
| `title` | `ACC claim reference set` |
| `status` | `draft` |
| `contact` | one contact with an (empty) email telecom |
| `description` / `purpose` / `copyright` / `jurisdiction` | **not populated** |

The resource is intentionally minimal metadata + one large enumerated code list.

---

## 2. Composition (`compose.include`)

A **single** include block, fully **extensional** (an explicit `concept` list — no
`filter`, so membership is exactly the listed codes, not an ancestor/descendant query):

| Field | Value |
|---|---|
| `system` | `http://snomed.info/sct` |
| `version` | `http://snomed.info/sct/21000210109/version/20251001` |
| `concept[]` count | **11,917** codes |
| `concept.display` | **absent** (codes only — no display terms in the resource) |

**Code system:** SNOMED CT, **New Zealand Edition**. The module/edition URI
`.../21000210109/...` identifies the NZ national extension; `20251001` is the
1 October 2025 edition release.

**Interpretation:** a diagnosis is "ACC-claimable" for the purposes of this product
if and only if its SNOMED CT concept id is one of these 11,917 codes.

### Sample of member codes (first 60 of 11,917)

```
262911006, 784408000, 82576008, 241790007, 191837001, 241789003, 46101007,
202187007, 202114006, 723135002, 80142000, 1489008, 201625003, 283372003,
282058007, 236564005, 82636008, 84920009, 207977001, 91419009, 721351009,
203223005, 209276008, 232279001, 90425003, 40970001, 241982001, 212205001,
21351003, 203681002, 209215000, 209288005, 209815008, 269236007, 36678001,
781449004, 202102003, 111689003, 35811000175104, 1156962001, 203296008,
17059001, 448768004, 283384001, 420198007, 201637001, 202175000, 202698007,
281916009, 81564005, 89298004, 283456007, 36269003, 128196005, 212145003,
270507001, 207904007, 212254008, 290622006, 283468003
```

(A handful of members are NZ-extension concepts — e.g. `35811000175104`,
`11808651000119103` — which only resolve against the NZ edition module, not the
international edition.)

---

## 3. Operations — what this endpoint can and cannot do

Tested live against the NZHTS FHIR base:

| Operation | Result | Notes |
|---|---|---|
| `GET ValueSet/acc-claim-reference-set` | ✅ returns the resource | gzip-encoded |
| `GET/POST .../$expand` | ❌ `404 not-found` | `"A usable code system with URL http://snomed.info/sct\|.../version/20251001 could not be resolved"` |
| `$expand` with `force-system-version` override (NZ 20250401/20241001, Intl 20250201) | ❌ `404 not-found` | server has **no** SNOMED edition loaded at all |
| `$validate-code` | ❌ (same root cause) | needs a loaded code system |

**Conclusion:** this is a **definition-only / repository** endpoint. It publishes the
value set *definition* but is not provisioned with the SNOMED CT substrate needed to
*expand* it. Therefore:

- You **can** read the exact code membership (the 11,917 SNOMED ids) straight from
  `compose.include[0].concept`.
- You **cannot** get display terms, a flattened `expansion`, or code validation from
  this endpoint.

### Getting display names / a resolved expansion

To obtain human-readable terms and a proper `$expand`, point at a terminology server
that has **SNOMED CT NZ Edition (module `21000210109`, edition `20251001` or later)**
loaded — e.g. an **Ontoserver** or **Snowstorm** instance. Then either:

```
POST {tx-server}/ValueSet/$expand
Content-Type: application/fhir+json
{
  "resourceType": "Parameters",
  "parameter": [
    { "name": "url",
      "valueUri": "https://nzhts.digital.health.nz/fhir/ValueSet/acc-claim-reference-set" },
    { "name": "count", "valueInteger": 50 },
    { "name": "filter", "valueString": "wrist" },       // typeahead search text
    { "name": "displayLanguage", "valueCode": "en-NZ" }
  ]
}
```

and validate a selected concept's membership + ACC eligibility with:

```
GET {tx-server}/ValueSet/acc-claim-reference-set/$validate-code
    ?system=http://snomed.info/sct&code=<selectedCode>
→ Parameters { result: true|false, display: "<preferred term>" }
```

`result: true` ⇒ the concept is in the ACC claim reference set ⇒ set the product's
**ACC? = Yes** flag; `false` ⇒ ACC? = No.

---

## 4. How the product consumes this value set

Restating the binding from the product spec, now grounded in the confirmed structure:

1. **Diagnosis typeahead** — bind the clinician diagnosis picker to this value set via
   `$expand?filter=<text>` against a provisioned SNOMED CT NZ server. Returned
   `contains[]` entries give `{ system, code, display }` for the grid.
2. **ACC? eligibility flag** — membership *is* eligibility. Because the set is
   extensional, you can even resolve the flag locally: cache the 11,917-code array and
   test `codes.has(selectedCode)`. Use `$validate-code` when you also want the server's
   preferred display.
3. **Body site / side** — captured as separate structured attributes (SNOMED laterality
   where possible); not encoded in the diagnosis concept itself.
4. **Version pinning & audit** — record `ValueSet.version = 20260401` and the SNOMED
   edition `21000210109/20251001` on each lodged claim, since both are versioned and the
   membership changes between releases.
5. **Refresh** — schedule a periodic re-pull of the value set (it's `draft` and
   date-versioned; expect updates). Diff the code set on refresh to catch
   added/removed claimable concepts.

---

## 5. Related FHIR resources for the full build (recommended, not all present on NZHTS)

The claim lodgement product touches more of the NZ health FHIR landscape than this one
value set. For a complete implementation, the relevant standards are:

- **SNOMED CT NZ Edition** `CodeSystem` (module `21000210109`) — substrate for the above.
- **NHI** identifier system — patient identity (`https://standards.digital.health.nz/ns/nhi-id`),
  with the NHI check-character validation rule applied in the admin UI.
- **HPI** (Health Provider Index) — provider/facility identifiers for the practitioner
  declaration and provider number.
- **NZ Base FHIR IG** (`build.fhir.org/ig/HL7NZ/nzbase`) — national profiles for
  `Patient`, `Practitioner`, `Organization` carrying NHI/HPI identifiers.
- **`Encounter`** — the visit created by the PAS/PMS that the whole claim is tied to
  (subject → Patient, participant → Practitioner, serviceProvider → Organization,
  period, location). The claim console is launched in encounter context; every claim
  artifact carries the `encounterId`. The ACC45 claim number is allocated at claim
  creation from a pre-allocated block or ACC's Claim Number Allocation API, and stored
  format-agnostically (the legacy number format is changing as the pool exhausts).
- ACC lodgement itself is currently transacted via PMS/HL7 messaging and ACC's provider
  APIs rather than a public FHIR write endpoint; model the `lodge` action as an
  integration boundary (stub in the mockup).

---

## 6. Reproduction notes

Everything above was read directly from the resource. To reproduce the membership pull
in a gzip-aware client:

```js
const vs = await fetch(
  'https://nzhts.digital.health.nz/fhir/ValueSet/acc-claim-reference-set',
  { headers: { Accept: 'application/fhir+json' } }
).then(r => r.json());

const codes = vs.compose.include.flatMap(i => (i.concept || []).map(c => c.code));
codes.length;                       // 11917
vs.compose.include[0].system;       // http://snomed.info/sct
vs.compose.include[0].version;      // http://snomed.info/sct/21000210109/version/20251001
```

---

## Sources

- [ACC claim reference set — NZ Health Terminology Service (FHIR ValueSet)](https://nzhts.digital.health.nz/fhir/ValueSet/acc-claim-reference-set)
- [SNOMED CT New Zealand Edition — Te Whatu Ora / Health NZ terminology](https://nzhts.digital.health.nz/)
