# Nadi compact UX proposal

Status: ready for design review, 7 September 2026. Application code unchanged.
Companion: [interactive mockup](../spec/nadi-compact-prototype.html).

## Intent and evidence

Give employees a useful first screen, one issue workflow, and an obvious place
to request equipment. Interpret “Plainview” as information visible at a glance.
Keep Nadi's lime identity, existing Vue/Ionic/frappe-ui stack, and shared Glass
components. Reduce decoration and motion. No new dependencies are proposed.

This review inspected current source and existing audit screenshots, not a new
signed-in production session. Historical screenshots may precede today's source.
The [September audit](../nadi-audit-2026-09-07.md) is supporting context; its old
test results are not new verification for this proposal.

| Finding | Evidence | Design consequence |
|---|---|---|
| Home has seven shortcuts, no KPI result or SOP preview | `frontend/src/views/Home.vue` | Replace shortcut menu with actual summaries |
| Two issue destinations occupy Home: Report an Issue and My Issues/Issue Board | same file | One Helpdesk summary opens the existing Issues destination; create there |
| Five tabs put KPI, Issues, SOPs and conditional management links in More | `data/navItems.js`, `views/More.vue` | Replace More only after assigning every destination a home |
| Creation already shares a single Employee Issue form | `views/issues/IssueForm.vue`, `IssuesTab.vue` | Extend it; do not build a second ticket form |
| Issue schema has three HR types and no title or support-team field | `hrms/hr/doctype/employee_issue/employee_issue.json` | IT/title/type needs an explicit schema and routing slice |
| Creation notifies HR; employees see tickets read-only; HR has internal notes | `employee_issue.py`, `IssueForm.vue` | Adding IT to a dropdown alone is insufficient and could expose HR information |
| No asset view, route or employee asset API exists in the inspected frontend/API | `frontend/src/views`, `router/index.js`, `hrms/api` | Assets is a real feature, not a renamed More menu |
| ERPNext Asset and Asset Movement exist locally | verify-bench ERPNext source; `full_and_final_statement.py` uses them | Reuse canonical assets; do not create another asset inventory |
| Home/Attendance/Leave use repeated 32px gaps; KPI has large score/trend blocks | corresponding dashboard components | Standardize spacing and prioritize actionable content |
| Home request aggregation masks missing resources as empty arrays | `components/RequestPanel.vue` | A failed summary must say unavailable, not zero |

## Navigation

Phone, fixed order: **Attendance · Leave · Home · Expenses · Assets**.
Home occupies the middle slot. All five keep equal size and touch areas.
Use a stable active indicator; no raised or pulsing Home button.

| Destination | Entry after More is retired | Existing URL preserved |
|---|---|---|
| Attendance, shifts, overtime, replacement leave claims | Attendance | `/dashboard/attendance` and existing forms |
| Leave balances, applications, holidays, replacement leave bank | Leave | `/dashboard/leaves` |
| Expenses | Expenses | `/dashboard/expense-claims` |
| KPI | Home KPI summary; desktop sidebar | `/dashboard/kpi` |
| Helpdesk (existing Issues, extended for IT/HR) | Home issue summary; desktop sidebar | `/issues`, `/issues/new`, `/issues/:id` |
| SOPs | Home pinned SOP previews and See all; desktop sidebar | `/sop`, `/sop/:id` |
| Team | Home management row and Profile, conditional on existing access | `/team` and roster route |
| Approvals | Home attention row and Profile, conditional on existing approver verdict | `/remote-approvals`; existing request approval flows |
| Notifications, profile, settings, HR contacts | Existing header/Profile | Existing routes |
| Assets and requests | Assets tab; desktop sidebar | Proposed `/assets`, `/assets/requests/new`, `/assets/requests/:id` |
| Old More links/bookmarks | Redirect to Home after all entries migrate | `/more` remains a compatibility route |

Desktop retains a full sidebar, including KPI, Helpdesk and SOPs. Use explicit
navigation objects, not fragile array positions/slices. Keep Ionic navigation
stacks; test child/detail routes, back, deep links and reloads.

## Home, in priority order

1. Compact header with notification and Profile controls.
2. Today: current attendance state and one Check in/Check out action. Keep
   geolocation, confirmation, missed-punch and offline behavior intact.
3. An attention row only when needed: attendance correction or approvals.
4. KPI row: actual score / 100 and exact cycle or annual-average label from
   the existing KPI API. No invented percentage, goal completion or due date.
5. Helpdesk row: own active issues (Open + In Progress), with status counts.
   The row opens Helpdesk. No second create button on Home.
6. SOPs: two published pinned titles the employee may read, plus See all.
   If there are no pinned items, offer the library; do not claim unread counts
   because acknowledgement/read tracking does not exist.
7. My requests: two recent/actionable items and access to a full history list.
   A complete combined history requires its own aggregation/pagination work;
   the current Home panel only takes ten and excludes some types from history.

Ordinary Home should show KPI, Helpdesk and SOP titles at 390×844 without
scrolling. Alerts, long translated text and enlarged text may increase height.
Never clip content to meet a screenshot target. Reduce scrolling, not access.

## Unified issues and helpdesk

Use the visible section label **Helpdesk** and action **New issue** everywhere.
An issue is one record, with one detail view, attachments and status history.
Existing HR issue links continue to work.

Proposed form: **Team (HR / IT), Title, Type, Details**, then compact optional
attachment and urgency controls. Keep urgency's existing Medium default.
HR types keep their current stored values and conditional leave/attendance
fields. Proposed IT types: Device, Software, Access, Network, Other IT issue.
These IT labels are a proposal, not established organizational categories.
Use “Send issue” as the create action; saving this non-submittable document
already files it, so do not add an unnecessary draft/submit lifecycle.

Contextual “Report a problem” links may prefill this SAME form with a type,
date or asset reference. They must not copy its fields or submission logic.
Repeated entry points can help; competing labels/forms cannot.

For HR, keep personal tickets available alongside the work queue instead of
replacing the personal list entirely. On phones use compact queue rows and
status filters; retain the existing board as a wider-screen alternative.

Backend approval needed before coding:

- Add a title and support-team field, IT types, and optionally an Asset link
  on Employee Issue. Preserve legacy records: blank team maps to HR; old
  titles get a deterministic non-sensitive fallback until a migration is agreed.
- Define IT staff membership and company scope using the site's actual roles.
  IT access must not grant access to HR tickets, notes or attachments. Audit
  every query, document API, attachment, notification and search path.
- Route IT notifications to IT and HR notifications to HR. Preserve existing
  status behavior and employee ownership restrictions.
- No comments/chat/SLA, automatic inventory mutation, or helpdesk integration
  is assumed. If an existing helpdesk is selected, use its canonical tickets
  and map legacy links, rather than silently maintaining two ticket systems.

## Assets

Default screen: **My assets**, with a clear **Request asset** action. A second
segment contains the employee's requests. Asset rows show name, identifier,
and assignment state; detail offers “Report a problem” into the shared issue
form with the asset prefilled.

Request form: asset category, quantity (default one), needed-by date, reason,
optional attachment. Show a specific existing asset only for a replacement
request when the source data supports it. Do not expose financial values or
the whole company's inventory in employee views.

Proposed request lifecycle: Pending → Approved/Rejected → Fulfilled. Approval
does not assign an asset. Fulfilment must follow the canonical ERPNext movement
process. Prototype statuses are examples, not a deployed workflow.

The local ERPNext checkout has Asset, Asset Movement and Material Request,
but no Asset Request doctype was found in its asset/stock modules. Before the
schema slice, determine whether the site's Material Request process serves
employee equipment requests; otherwise approve a thin request doctype linked
to existing assets. Do not repurpose Employee Issue as an inventory ledger.
Confirm approver/fulfiller ownership and target-site capabilities in that slice.

## Every screen: density and action hierarchy

| Screen family | Main action and layout |
|---|---|
| Home/check-in | Attendance state + Check in/out; compact summaries; resolve exceptional state visibly |
| Attendance | Today/week first; month expandable; correction, shift and OT actions in a compact group; recent rows |
| Leave | Balances + Apply for leave first; requests next; holidays and replacement bank compact |
| Expenses | Summary + Claim expense above recent claims; receipt on detail |
| KPI | Score and period in one row; KRA actual/target rows; trend secondary |
| Helpdesk | New issue; searchable personal list; HR/IT/type/status filters; role-scoped queue |
| Issue creation/detail | Visible labels, conditional fields, one send action; read-only status/attachments on detail |
| Assets | Request asset; My assets/Requests; one scoped request detail |
| SOP list/detail/edit | Search first; compact pinned list; readable full document; HR edit separate from row navigation |
| Request lists | Shared row, filter, status and pagination pattern; one meaningful creation action |
| Attendance/leave/expense/shift/OT forms | Shared FormView; dense sections; full-width phone inputs; attachments collapsed until needed |
| Team/roster/approvals | Counts, filter and queue first; decision stays on selected request; keep existing confirmation rules |
| Notifications | Compact unread rows; mark-all secondary; failure and retry visible |
| Profile/contacts/settings/password | Compact groups and stable back control; account/security behavior unchanged |
| Login/reset/invalid employee/not found | Clear heading and recovery action; no large decorative empty panels |
| Shells, sheets, upload and preview | One header; keyboard-safe footer; correct return path; full document zoom remains available |

Proposed shared measurements: 16px phone gutters; 12–16px section gaps;
48–56px ordinary rows; 44px minimum interactive targets; 16px inputs;
14–16px body text; 20–24px page headings. Keep readable SOP prose.
Use one primary action per task context, neutral secondary actions and plain
view-all links. No duplicate page titles or unnecessary uppercase eyebrows.

Keep light and dark themes. Retain Glass identity mainly in app chrome; use
stable readable content surfaces. Remove glow/pulse/scale effects and moving
backgrounds. Color feedback may last at most 120ms; no layout motion on tab
changes. Respect reduced motion, visible focus and sufficient contrast.
320px reflow and larger text must remain usable, following
[WCAG reflow guidance](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html).

## Implementation after approval

This proposal does not supersede the current design spec until approved.
Record approved changes to navigation, density, material and motion in a spec
addendum before editing tokens; regenerate rather than hand-edit generated CSS.

1. **Design contract and shared shell.** Spec addendum; tokens; GButton,
   GListRow, GPage, BaseLayout and form primitives. Check existing consumers
   and both themes. Commit one concern at a time inside source-line budget.
2. **Home and navigation groundwork.** Shared summary resources, visible
   error/empty/loading states; preserve existing routes and manager entries.
   Place Home centrally; keep More temporarily until Assets is usable.
3. **Unified Helpdesk.** Approved schema/access/routing plan, failing tests,
   then shared issue title/team/type implementation and backward compatibility.
4. **Assets.** Approved request model and ownership, employee-scoped reads,
   creation, approval and fulfilment contracts, tests and frontend. Replace More
   with Assets only when it works; redirect More and verify every old entry.
5. **Remaining screens.** Attendance/Leave/Expenses; lists/forms; KPI/SOP;
   Team/approvals; account/recovery. Use the inventory above to track coverage.

Verification for application slices: relevant tests red first for features/fixes;
mapped unit/Python tests; importer tests and smoke; navigation/deep links;
employee/HR/IT/manager visibility and cross-company denials; no duplicate record
on repeated submission; attachment access; required/conditional fields; loading,
empty, partial error and offline states; keyboard/focus; 320/390/768/1440 widths;
both themes and reduced motion; current design gates with explicit baseline
review, not blanket replacement. Run code review before push. Deployment and
post-deploy evidence remain a separate authorized phase.

## Review scope

The HTML is an interactive design artifact with labelled sample data, navigation,
filters and demonstration forms. It never calls application APIs or creates real
records. Detailed transactional workflows are specified here, not implemented
by the prototype. Approval requested: navigation, Home order, compact visual
direction, and one shared HR/IT issue experience. Asset data model and access
changes require their concrete backend plan before implementation.

## Prototype verification

Run: `node docs/glass/spec/nadi-compact-prototype.check.mjs` using the installed
frontend Playwright and axe dependencies. Latest run: exit 0; 17 screens ×
4 widths (320, 390, 768, 1440) × 2 themes = 136 overflow checks, zero failures;
34 automated accessibility scans, zero violations in the configured WCAG tags;
zero JavaScript errors. Nine interaction checks cover navigation, HR/IT filtering,
conditional fields, asset-to-issue context and demonstration form submission.

Home's second SOP row ends at y=699; bottom navigation begins at y=779 on
390×844, including the prototype review toolbar. Home screenshots hide that
toolbar to show the proposed application view. Manually inspected light/dark
Home, Assets and New issue screenshots. `git diff --check` passes.
These are prototype checks, not evidence that the real features work or that
all accessibility requirements are satisfied. Application tests were not rerun
because no application code changed. The detailed JSON result is alongside
the HTML as `nadi-compact-prototype-checks.json`.

Pending: design approval. IT support is provisionally designed inside Nadi;
no answer to the optional existing-helpdesk question has been received.
