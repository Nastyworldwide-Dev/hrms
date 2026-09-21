# Phase 2 ground truth — what the real frontend is, before any of it is changed

Section 1 of the implementation brief: "Inspect architecture, routes,
components, state, API client, styling, packages, tests, build config" and
"confirm the mockup is implementable with current backend responses" BEFORE
writing code. This is that inspection. Nothing here changes a file.

## What exists

Vue 3 + Ionic Vue 7 PWA, Vite, `frappe-ui` for the data layer, Tailwind.
Scripts: `lint` (eslint), `test` (node --test), `build`, `gates`, `test:e2e`.

- **45 named routes**, 38 of them with visual baselines (115 PNGs at 390 and
  1440, light and dark).
- **42 Glass components** under `src/components/glass/`, plus 47 feature
  components.
- **Design system is generated**: `design/tokens.json` -> `build-tokens.mjs`
  -> `frontend/src/theme/glass.variables.css`. tokens.json is the single
  source of truth and is itself downstream of the spec. Hand-editing the CSS
  is explicitly forbidden by `design/README.md`.
- **Eight gates** in `design/gates/`: lint, usage, contrast, surfaces, tokens,
  a11y, visual, coherence. The contrast gate COMPUTES WCAG ratios from
  tokens.json rather than trusting the spec table, and alpha-composites glass
  over the app background first. a11y and visual are render-time and skip
  without a running site.

## The conflict that has to go to the owner

**The mockup's five tabs are not this app's five tabs.**

| | mockup | app (`data/navItems.js`) |
|---|---|---|
| 1 | Home | Home |
| 2 | Calendar | Attendance |
| 3 | Requests | Leaves |
| 4 | Score | Expenses |
| 5 | More | More |

This is not a restyle. The mockup proposes a different information
architecture: one Calendar that absorbs attendance + roster + claims, and one
Requests screen that absorbs six separate doctype lists (Leave Application,
Expense Claim, Shift Request, Attendance Request, OT Request, Replacement
Leave Claim — `data/requestLists.js`).

Three things make this expensive rather than cosmetic:

1. `navItems.js` says the five destinations are FIXED by design, because
   "a bar whose destinations change under the user breaks Ionic's per-tab
   navigation stacks". Changing the set means re-testing every stack.
2. The current fourth slot is already a recorded compromise: §13.1 asks for
   PAY, there is no salary-slip route, so Expenses stands in — and the file
   says DECISION 2 is "not signed off".
3. Merging six request lists into one screen is a real feature with real
   permission surface (each list has a `my` and a `team` variant), not a
   layout change. The brief forbids touching backend or permissions.

**Question for the owner, not for me to decide:** is Mockup 4 a visual
contract (colours, spacing, depth, motion, component shapes — applied to the
screens that exist) or an information-architecture contract (these five tabs,
these merged screens)? The first is Phase 2 as scoped. The second is a
product change that needs its own plan.

## Smaller divergences, same question

- Mockup "Score" vs app KPI: the app's KPI is tier-gated by DESIGNATION on the
  server (`data/kpi.js` — a role gate would have leaked every appraisal score
  to HR). A "Score" tab for everyone has to respect that gate.
- Mockup has 11 screens and 5 sheets. The app has 45 routes. The mockup does
  not cover SOPs, Helpdesk/Issues, Team, Roster, Remote Approvals, Settings,
  Change Password, HR Contacts, or any of the 13 form/detail views.

## What Phase 2 can start on without an answer

The brief's own section 3 work — tokens, type, spacing, radii, surface and
blur rules, motion — applies to every screen regardless of which tabs exist,
and is generated from tokens.json rather than hand-written per screen. The
per-screen work in section 2 cannot start until the question above is answered,
because "Home, Calendar, Requests, Score, Settings" names three screens this
app does not have.
