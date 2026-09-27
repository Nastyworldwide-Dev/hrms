# Nadi 2.0.0-alpha.14 — plan (27 Sep 2026, revision 2)

**Goal.** A whole-app pass, not a list of the owner's screenshots: every screen, sheet, row and role in the PWA held to Apple's rules; the Desk held to standard Frappe; the roster and the approver calendar brought up to what leaders need; security and performance swept; and the checks upgraded so an installed iPhone is what we test.

**Two rulebooks, never mixed.**
- **PWA (Nadi):** Apple HIG (`docs/glass/audit/2026-09-26-a12/rules.md`).
- **Desk (the Frappe back office, "Verifica"):** standard Frappe patterns only — list/form views, Frappe UI conventions, workspace, reports, no custom look.

Evidence for everything below: 36 screens re-shot in dark mode on an iPhone profile (`docs/glass/audit/2026-09-27-a14/screens-review.md`), plus a role inventory (`roles.md`), a roster map (`roster.md`) and a calendar map (`calendar.md`) in the same folder, read from code and the test site.

---

## 1. Why the owner's defects got past us (fixed first)

Our gates ran in WebKit at iPhone size, which is not the installed app on an iPhone:
- no safe areas (status bar, Dynamic Island, home indicator);
- every page loaded straight from its URL, never reached by tabs, scrolling and pulling;
- test data with short names, no photos, and one leave type.

**Slice 0.** The gate profile becomes an installed iPhone: safe areas on, standalone mode, a journey script (tab → scroll → switch → back → pull), real-length names and a check-in with a photo. It must go red on today's build for the owner's items before any fix.

---

## 2. Every role that has more than a plain employee

| Role | Who gets it | What it adds | Where it is enforced |
|---|---|---|---|
| **Approver** (not a role: a relationship) | anyone who is someone's `reports_to`, a named leave/expense/shift approver, or a Department Approver | Approvals queue for their people; team calendar (who is off, type only, never the reason); Team page | `team.is_approver`, `approval.py` routing, `calendar._who_is_off` |
| **Leave Approver** | the "HR" role profile | Desk: read/submit/cancel leave | Leave Application permissions |
| **Expense Approver** | the "HR" role profile | Desk: expense claims and advances | Custom DocPerm |
| **Shift Supervisor** | assigned per user by IT/HR | Roster their **own direct reports** in permitted companies (PWA + Desk). Desk: Shift Assignment read/write/create/submit; Shift Schedule (+ Assignment) write; Shift Type/Location read | `roster._ensure_can_roster`; patch `add_shift_supervisor_role` |
| **HR User** | the "HR" role profile | Sees everyone's HR data in their companies; HR-only PWA pages (Issue Board, SOP editing, directory); Fix attendance; roster anyone in their companies | `hr.utils.is_hr_operator`, `sees_all_employee_data` |
| **HR Manager** | the "HR" role profile | HR User plus delete in Desk | DocPerm |
| **HR (Company) / HR (Instance) / HR Manager (Group)** | company-fence roles | Narrow (or not) which companies HR sees — no extra actions | `company_fence.py` (User Permissions) |
| **System Manager** | IT | Everything in Desk; **deliberately not** an HR operator in the PWA | `HR_SEE_ALL_ROLES` excludes it |

**Checked and correct:** every power is enforced on the server, not only in the screen. Read fences: `_ensure_own_employee_or_permitted`, `_may_read_employee`, `own_employees`. Write fences: `_ensure_can_roster`, the approval routing.
**To make visible:** HR has no page that lists who holds which of these. **Add:** a Desk report, "Who can do what", listing each user's roles, role profile, companies, team size and Shift Supervisor scope (standard Frappe Script Report, HR-only).

---

## 3. Roster (owner: "we kinda forget about roster")

**Today.** The Desk roster app (`/hr`, month view) and the PWA Team → Roster week view share one API (`hrms/api/roster.py`).
- **HR** can roster anyone in their companies.
- A **Shift Supervisor** can roster only their direct reports (`reports_to`).
- Branch and department are shown as filters but **do not decide who a supervisor may roster**.

**Owner's ask:** HR sets team leaders/supervisors per branch in Desk; HR can roster on a leader's behalf.

**Proposed:**
1. **Scope by what HR sets, not only `reports_to`.** HR, in Desk, can give a Shift Supervisor one or more **branches** to roster (standard Frappe: a child table on the Employee or a "Roster Scope" doctype). A supervisor may roster their direct reports, **plus** everyone in their assigned branches. HR keeps "anyone in my companies". *(Needs ruling R10.)*
2. **HR acts for a leader, visibly.** In the PWA and Desk roster, HR picks "Roster for: <leader / branch>". Every change records "by HR on behalf of <leader>", which the leader sees on the week.
3. **Warn, don't block.**
   - Assigning a shift on a day someone is on approved leave or a public holiday shows "On leave" / "Holiday" on that day, and the save asks first.
   - Today nothing warns (`insert_shift` / `break_shift` do not read leave or holidays).
4. **Past weeks locked** after payroll cut-off (16th–15th pay window, already a ruling): read-only unless HR. *(Needs ruling R11.)*
5. **Publish and notify.** A week is a draft until the leader taps **Publish**; staff get one notification per week ("Your shifts for 29 Sep – 5 Oct"), not one per cell.
6. **Desk roster: standard Frappe.**
   - The month view keeps Frappe's look.
   - Fixes: its filters use the same scope as the API; empty and error states; a legend for shift colours; the leave/holiday overlay.
7. **Tests:** the fence (supervisor ↔ other branch refused), the leave warning, the lock, the publish notice.

---

## 4. Calendar for approvers and team leaders

**Today.**
- The month grid is **your own** days only, plus a dot for requests waiting on you.
- The team's day lives on a separate Team page: who's in, when they came, and who's off (leave type only).
- A day sheet from your own calendar shows "who is off" and coverage counts.

**Proposed (all fenced to the leader's own team; HR can pick a team):**
1. **One calendar, a Team switch** at the top: **Me | Team**. Team turns the grid into the team's month.
2. **Team month grid.** Each day shows how many are off and a warning mark if someone was absent without leave or late, plus the "waiting on you" dot. The tile shows numbers, never names.
3. **Team day sheet**, grouped:
   - **Off** (name · leave type · half day). The reason is never shown (standing ruling).
   - **Not in yet / absent**.
   - **Late** (arrived after shift start + grace).
   - **Waiting on you** (requests for that day), each opening its approval sheet.
   - **Shift changes and swaps**.
   - **Holiday** (by the member's holiday list).
4. **Coverage line:** "7 of 9 in · 1 off · 1 not in yet".
5. **Privacy stays as ruled:**
   - type, never reason;
   - direct team only;
   - HR can browse any team in their companies;
   - "no team" and "team has nobody today" say different things.

---

## 5. The owner's screenshots, and the same classes everywhere

| # | Seen | Fix (app-wide) |
|---|---|---|
| A | Check-in sheet: "Employee Checkin", loud latitude/longitude, photo as a file name | Sheet titled "Check-out · 1:55 am"; the **photo itself**; "Where: Inside Damansara · 40 m". **Coordinates kept, quiet**: a small secondary line "3.17437, 101.68543" under Where, tap to copy (for tracing, per owner). **Every attachment in the app previews**: images inline, PDF first page, others as a typed file row |
| B | Check-ins list: time floats mid-row | Time on the trailing edge by the chevron; IN/OUT icon; a day summary "9:00 am – 6:00 pm · 9h" |
| C | Two titles (bar + large) | The bar's small title follows the live scroll position; reset on tab show |
| D | Tall gap above every page; tab bar placement | Tab roots: the large title sits in the bar's second row, the Nadi mark removed from the bar (Apple: no logo in nav bars). Pushed screens: one 44 pt bar. Tab bar 8 pt above the home indicator |
| E | Requests: "Annual 6 · Medical 13" cramped | A compact two-up balance strip (number · word · thin used/total bar), mockup first |
| F | You: manager name wraps into 3 right-aligned lines | Long values stack under their label (Apple typography: stacked layout), every row in the app |

**Found in our own sweep (not in the screenshots)**, fixed at the shared component:

| # | Seen | Fix |
|---|---|---|
| G | Decided requests still offer "Add a file" | Hidden once decided |
| H | Detail status squeezed into the nav bar ("Approved, not …" truncated) | Status as a badge row at the top of the content; the bar keeps only the title |
| I | "Hours  Required ▮": a stray block from the number field's native spinner | Spinner hidden on all number fields |
| J | "What are you reporting?  Requirec": value cut | Row values truncate with an ellipsis, never mid-word; a picker's value leaves room for its chevron |
| K | Six different icons and wordings for "nothing yet" | One empty state: one line saying what is true, plus the action |
| L | Score: a card with a brand-colour left bar (colour as decoration) | A grouped row |
| M | "Days left before this 19" on a request | Moves to the balance, not the request |
| N | "Include holidays" (Fix a day) is jargon; the password rules are shown only after a failure | Plain words; the password rule shown up front as the field footer |
| O | Approvals lives under You; More has 4 rows | Leaders' things (Approvals, Team, Roster) in one "Your team" group on More; You is only you |
| P | Version line shows the build date and time | **Version and release name only**, no date/time (owner) |

**Versioning (owner, R12 ruled 27 Sep: professional, no themed names).** Each release is named for what it delivers, in plain words: "Nadi 2.0.0-alpha.14 — Roster and Team Calendar". The name is set once in `package.json` (`releaseName`) and used by the changelog heading, the GitHub Release title and the You page. No dates or times anywhere in the app.

---

## 6. Security, authn/authz, performance

| # | Finding | Evidence | Fix |
|---|---|---|---|
| S1 | **Shared phone: after log out, the last user's page could open offline** (page cache from alpha.12 not cleared) | `public/sw.js:39` "nadi-pages"; nothing deletes it | Clear the page cache on log out and user change; test |
| S2 | Push subscribe/unsubscribe write over GET | `hrms/api/push.py:21,29` | POST only |
| S3 | Check-in photos are private (verified `is_private: 1`); the new preview must use the permission-checked file route | `remote_checkin.py:682` | Preview through the private route; a stranger is refused (test) |
| S4 | Endpoint sweep: 20+ checked and fenced; ~100 not yet checked one by one; CSRF on every write not yet checked | security sweep, 27 Sep | Full sweep: one test per finding |
| S5 | Roles are enforced server-side (checked), but HR cannot see who holds what | §2 | "Who can do what" Desk report |
| P1 | First paint ~5.4 s on a slow phone; Ionic core is most of what is left | alpha.13 measurement | Per-component Ionic imports; target < 5 s |

---

## 7. Order (one cause per commit, red first)

0. Installed-iPhone gate profile and journey (§1)
1. S1: clear the page cache on log out (security first)
2. S2: push POST-only
3. C: double title; D: top gap and tab bar
4. B: check-ins row; F: long values stack; J: truncation; I: number spinner
5. A: check-in sheet, quiet coordinates, previews for every attachment
6. G, H, K, L, M, N, O, P: shared fixes, and the release name
7. E: balance strip (mockup, owner sign-off)
8. Calendar Me | Team (mockup, owner sign-off)
9. Roster: scope, on-behalf, warnings, lock, publish (rulings R10/R11), Desk touch in standard Frappe
10. S4 endpoint and CSRF sweep; S5 "Who can do what" report
11. P1 Ionic per-component

Then: every gate at 402 / 820 / 1280 with safe areas, light and dark → full visual re-baseline → `2.0.0-alpha.14 · <Name>` → `scripts/release.sh`.

## 8. Rulings

**Ruled 27 Sep:** R10 yes (branch scope set by HR in Desk). R11 yes (lock after pay cut-off). R12 professional descriptive names, no themes. R8/R13 mockups before build: yes.

**Roster is a new feature: its design waits on facts, not guesses.** See `docs/glass/plan/ROSTER_FACTS_NEEDED.md`. Slices 0–8 and 10–11 do not depend on it and go first.

### Originally asked
- **R10:** Should a Shift Supervisor also roster everyone in branches HR assigns them, not only their direct reports? *(recommended: yes, set by HR in Desk)*
- **R11:** Lock past roster weeks after the pay cut-off (16th–15th) for everyone except HR? *(recommended: yes)*
- **R12:** The release name list: a plain theme (for example Malaysian rivers: Klang, Pahang, Rajang, …)? *(owner's choice)*
- **R8:** Approve the balance strip mockup, and **R13** the Calendar Me | Team mockup, before they are built.
