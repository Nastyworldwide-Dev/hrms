# PRE-2.0 — five releases, then 2.0 starts

TIER: risky (many files, forms, security, the PWA's own API layer)
SCOPE: the Nadi PWA and `hrms/api/` — the PWA's OWN backend. NO Desk, no
doctype JSON, no workspace, no report, no hooks beyond what api/ needs.
OWNER RULINGS, 22 Sep 2026: decision 2 NO (no PAY tab) · 3 FIX (iOS input
zoom) · 4 unanswerable, assume and record · 5 FIX (10px type floor) · 6 this
branch IS the official version. Max 5 releases. Sections 10 and 16 ARE in
scope because api/ is the PWA's own layer, not Desk.

## R1 · Safety net
- `v-html` at 4 sites (Notifications, SopDetail, TicketDetail, loudRequest)
  has no sanitiser. Server-controlled today, one field from XSS.
- Inputs render at 12.5px (`--g-type-row-label-size`); iOS zooms the page on
  any input under 16px. 18 screens.
- Type floor 10px (spec §4.2, DECISION 5).
DONE WHEN: a test fails on an unsanitised v-html; inputs are >=16px at the
point of focus; no token under 10px.

## R2 · API contract
- ~60 of 115 endpoints do not pin their HTTP method. No writer is GET-exposed
  today — verified — so this is a gate against the next one.
- 15 endpoints carry no visible guard; two of them write.
- Nothing checks that the endpoints the PWA calls still exist and answer the
  shape it reads.
DONE WHEN: every endpoint pins a method; every one has a guard or a recorded
reason; one test maps every `hrms.api.*` string in src/ to a real endpoint.

## R3 · Reliability
- `navigator.onLine` appears nowhere; the offline banner has no trigger.
- `skipWaiting()` takes a new build over mid-session, mid-form.
- 401 and 403 are not handled distinctly everywhere.
- Double-submit: audit every form's pending state.
DONE WHEN: going offline shows the banner; an update waits and asks; a
duplicate submit is impossible from the UI.

## R4 · Accessibility + observability
- WCAG 2.2 AA over forms: labels, errors tied to fields, modal focus traps.
- No frontend error capture, no build version on requests.
DONE WHEN: every field has a label and its error is linked; modals trap focus;
errors reach a log with the build id and nothing sensitive.

## R5 · Measure
- Every recorded number predates the bottom-nav repair and understates
  overflow by ~65px. Re-measure at 360x640 and 390x844, re-bake baselines,
  check 320px.
BLOCKED: needs a reachable site. Owner: "if site is inaccessible its okay."
So R5 ships the HARNESS and the source-level checks; the numbers wait.

## Not in scope, and why
TypeScript (checklist 15) — this is a JS codebase; converting it is its own
project. Core Web Vitals, browser matrix, real screen-reader passes — all need
a site. Desk, doctypes, workspaces, reports — owner's word.
