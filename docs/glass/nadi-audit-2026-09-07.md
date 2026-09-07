# Nadi audit — Desk and PWA, 7 September 2026

Audit only. Nothing in the app was changed. Branch `nz-glass` at `5af6e6541`.

Measured against a running site (`fresh.local` on verify-bench, Frappe 16.31,
served on :8080, bundle built 3 Sep) plus the source tree. Where a claim
comes from the site it says "bench"; where it comes from source it gives a
path. One probe row (a draft Attendance Request) was created on the dev site
by mistake during the e2e diagnosis and removed again.

## Instruments run

| Check | Result |
|---|---|
| `yarn lint` (frontend) | clean |
| `yarn test` (frontend, node:test) | 138 / 138 pass |
| bench-free Python tests (`PYTHONPATH=. python3 hrms/tests/test_*.py`) | 34 files pass; 3 need a bench (`test_company_api_scope`, `test_offboarding_integration`, `test_pwa_forms_have_no_dead_controls`) |
| design gates, static (lint / usage / contrast / surfaces / tokens) | all at baseline: lint 227 known 0 new, contrast 54/54, surfaces 0 over, tokens 6 known collapses |
| design gate a11y (rendered, 76 screen-themes) | 0 new; 26 baselined critical/serious remain |
| design gate coherence (rendered, 38 screens) | **1 violation**: `forgot-password` has no back control (it is a dialog on Login, `Login.vue:112`) |
| `critical-paths.spec.js` (rendered, signed in as the audit employee) | 3 pass, **2 fail, 1 skipped** — see F1 |
| visual gate | not run (16 known unclassified diffs, 30 min) |

## Critical

### D1. Every employee sees all nine HR workspaces in the Nadi launcher and their sidebars — including Payroll and Tax & Benefits
- Bench, as `nurul.aisyah@` (Employee + ESS only): `bootinfo.desktop_icons` children of Nadi = Expenses, HR Setup, Leaves, Payroll, Performance, Recruitment, Shift & Attendance, Tax & Benefits, Tenure. The Payroll sidebar lists Salary Structure Assignment, Salary Slip, Salary Withholding, Income Tax Deductions, Professional Tax Deductions.
- Cause: the `gate_hr_workspaces_to_hr_roles` patch put roles on the Workspace **page** only. In v16, "Workspace Sidebar" desktop-icon children and sidebar items are filtered by doctype read permission, not workspace roles (`frappe/desk/doctype/desktop_icon/desktop_icon.py:176-181`, `frappe/boot.py:441-505`). ESS has read on the payroll doctypes.
- Why it matters: `decisions/payroll-stays-out-of-verifica.md` and `who-sees-what-in-nadi.md` say HR alone sees these. Desk shows them to staff.
- Fix: add `roles: [HR User, HR Manager, System Manager]` to the nine child icons in `hrms/desktop_icon/*.json` (Desktop Icon honours its roles table) and bump `modified`. Sidebars have no roles field; either drop the ESS read on payroll doctypes or record the exposure.

### D2. Two payroll reports are open to every Desk user on existing sites
- `hrms/payroll/report/professional_tax_deductions/*.json` and `provident_fund_deductions/*.json` add HR roles in the JSON but `modified` is still `2022-06-26`, so the timestamp-gated import never lands. Bench: both have zero `Has Role` rows. Frappe treats zero roles as visible to all. `scripts/check_fixture_timestamps.py --since version-15` flags both (rc 1).
- Today the run is stopped only because ESS lacks the `report` ptype on Salary Slip. One Custom DocPerm edit away from a leak. `test_workspace_access_gating.py` reads the JSON only, so it is green while sites are wrong.
- Fix: bump `modified` on both JSONs and add them to a patch that sets the roles on existing sites.

## Important

### F1. The critical-path e2e suite is red for a different reason than THE_PLAN says, and the approval test has never run
- THE_PLAN 2.4 / READINESS 1.1 blame `cache: "hrms:leave_balance"`. Not so. Test 4 (`critical-paths.spec.js:94`) navigates to `/hrms/leaves`; the route is `/dashboard/leaves` (`router/index.js:36`), so it lands on `NotFound` ("That page isn't here", screenshot in `frontend/test-results/`). Test 3 (`:72`) signs in and asserts on Home, but Home has no leave-balance panel — `LeaveBalance.vue` is mounted only by `views/leave/Dashboard.vue:14`.
- Proof: a throwaway copy of both tests pointed at `/hrms/dashboard/leaves` passed 2/2 in 3 s against the same site. The app is fine; the tests aim at the wrong page. Do not weaken the assertions; fix the URLs.
- Test 5 "approving a request does not leave it asking to be submitted" (`:138`) **skips on every run** with `could not seed a draft: 400`. Reproduced with curl: after the app boots, a REST POST without `X-Frappe-CSRF-Token` returns `CSRFTokenError`. The `api()` helper at `:126-133` sends no CSRF header. So the one test written to catch Mirza's "approval did not stick" has never executed. Fix: read `window.csrf_token` (or `frappe.csrf_token`) in the page and send it as `X-Frappe-CSRF-Token` in `api()`.

### F2. Home's Requests panel turns a failed fetch into "Nothing here yet"
- `RequestPanel.vue:7-15` passes only `:items` to `RequestList`, never `:resource`, so `RequestList.vue:2`'s `ResourceError` cannot fire. Six merged resources (`:74-102`); a 403/500 on any of them renders the empty state. The four dashboards do pass `:resource`. The static exemption in `hrms/tests/test_pwa_resource_states.py:53` assumes the parent owns the error; this parent does not.
- Fix: a `ResourceError` per contributing resource in `RequestPanel`, and extend the static gate so a `RequestList` without `:resource` is an offender unless the parent renders its own error.

### F3. No offline handling in the PWA
- No `navigator.onLine` / `online` / `offline` usage in `frontend/src`; `public/sw.js` is push-only; `vite.config.js:18-24` precaches only; a punch is one `punchCheckin.submit` with a toast on failure. GATE 3 9.7b ("the only P0") is fully open.
- Fix (minimum): online/offline listener that disables the punch button with a visible banner. Queueing is the GATE 3 spec.

### D3. GATE 0 exit criteria that the shipped JSON cannot meet
- "Shift Assignment Tool back in the Shift & Attendance sidebar": `hrms/workspace_sidebar/shift_&_attendance.json` has no such item (bench agrees); it is only on the workspace page. No commit ever added it.
- "HR Setup shows the Data Migration card": `hr_setup.json` has the links but `content` blocks are Setup, Employee, Leaves, Settings, Attendance, Expense Claim, Key Reports, Other Reports — no `Data Migration` card block, and v16 renders cards from `content` only. Fix: append `{"type":"card","data":{"card_name":"Data Migration","col":4}}` and bump `modified`.

### D4. HR Outstanding is unreachable from the launcher and re-imports on every migrate
- No desktop-icon child, no sidebar (9 of each for 10 workspaces). Reachable only via the auto-generated `hr` module sidebar or a typed URL. Its JSON has no `modified`/`creation`, so `import_file.py:124` treats it as new on every migrate and silently reverts any Desk-side edit.
- Fix: add `hrms/desktop_icon/hr_outstanding.json` + a sidebar (or record "URL-only by design"); add a `modified` stamp.

### D5. Frappe auto-generates an `HR` module sidebar for employees
- No `Workspace Sidebar` named "HR" exists (Payroll has one), so `workspace_sidebar.py:243` builds one each boot. Bench, as the employee: 12 items incl. the Human Resource / Employee Lifecycle dashboards, Employee Advance Summary, Organizational Chart. Data was row-scoped when run (no leak found), but staff are offered HR dashboards.
- Fix: ship a minimal standard `Workspace Sidebar` named `HR`.

### D6. `role-access-matrix.md` has drifted
- Missing: `Shift Supervisor`, `HR (Instance)` / `HR (Company)` fence roles, Employee/ESS read on Currency. Travel Request says `rwc`, bench shows `rwcd`. Employee Advance absent although Employee/ESS/Expense Approver hold read and its report is Employee-visible. Fix: regenerate from the bench per the doc's own "How to re-run".

### D7. Employee Advance is read-only by policy but still wired across Desk
- Sidebar item in `expenses.json`, links in Expenses and HR Setup, `Employee Advance Summary` linked from two HR pages while its roles are `Expense Approver, Employee` only (HR cannot open it). `employee_advance.js:37-90` still adds Payment / Expense Claim / Return buttons.
- Fix: drop the sidebar item and the HR-page report links, or add HR roles to the report and bump `modified`.

### F4. Critical paths still without a test
- Now covered: login, forgot-password, forced-500 balance, balance renders, approval via `finalize` (once F1 is fixed), check-in sheet to Confirm.
- Still none for: a punch creating exactly one Employee Checkin row (2.1), expense claim submit, leave apply/submit, HR Settings save (2.3), Reject via `decide`, offline.

## Minor

- **S1 (security warning)** `hrms/api/__init__.py:1313` `get_doctype_fields` and `:1361` `get_doctype_states` take any `doctype` and return its meta with no read check on the doctype itself. Any signed-in user can enumerate the field schema of Salary Slip or HRMS ERP Instance (values stay hidden). Fix: `frappe.has_permission(doctype, "read", throw=True)` at the top of both.
- **S2** `employee_checkin.py:139-198` `add_log_based_on_employee_field` accepts an unbounded client `timestamp`. Gated by real create permission (device/API accounts only), unlike the PWA punch which pins server time. Fix: clamp to a window.
- **F5** More → Team entry gates on `hasTeam` (`More.vue:46-54`), narrower than the remote-checkin approver chain (shift approver → department approver → reports_to → HR). A named approver without reports gets Profile and the Home banner but no More entry. Fix: gate on `isApprover` like Profile.
- **F6** Two `v-html` sinks (`views/sop/SopDetail.vue:48`, `views/Notifications.vue:88`) rely on Frappe's server-side sanitiser; safe while writes go through `doc.insert`/`set_value`. Note in the sync write rules that a `db_insert` path would bypass it.
- **F7** `data/session.js:19` logs the login email to the console.
- **F8** `Notifications.vue:54` passes the MouseEvent into `markAllAsRead.submit`.
- **F9** Dead whitelisted surface: `get_salary_currency`, `approval.report_half_transitioned`, `erp_instance.get_my_erp_instance` (docstring promises a button that does not exist).
- **D8** Performance workspace links `Energy Point Rule/Settings/Log`, which do not exist in v16 (bench: 3 broken links); its four cards are not in `content` so they never render.
- **D9** `hrms_erp_instance.js` shows Purge / Sync / Parity buttons to anyone who can open the form; server is `only_for(...)`, so HR User gets 403 on click.
- **D10** Nine desktop-icon children all have `idx: 0`; modal order is DB insertion order.
- **D11** `gate_hr_workspaces_to_hr_roles.py` docstring says workspaces are not re-synced on migrate; they are, timestamp-gated (`frappe/model/sync.py:35`).
- **D12** `onboard: 1` on Job Opening and Attendance links with no onboarding shipped.
- **C1 (coherence)** forgot-password dialog has no back control (`Login.vue:112-140`).
- **Docs drift** THE_PLAN lists as open items that are closed in code: 3.1 (OT Request notifies via `PWANotificationsMixin`, `ot_request.py:54,65`), 3.3 (`test_pwa_resource_states` 7/7), 3.5 (`status` field on OT / Attendance Request / RL Claim, all in `DECIDE_THEN_SUBMIT`), 3.6 (`/dashboard/kpi` is a full Appraisal screen). `RequestPanel.vue:96-101` still excludes those three from History on the old "no status field" premise.

## Info

- THE_PLAN 4.1 (`run_sync` on the scheduler) is not done: `hooks.py:547-608` schedules only `report_stale_instances` and `report_readiness`.
- `/desk/people` (`hooks.py:10,17`, Nadi icon link) names no Workspace or sidebar in the repo or on the bench. With one permitted child the icon opens the modal instead, so it is hit only from the apps screen. Could not verify what it renders.
- The PWA bundle and `hrms/www/hrms.html` are gitignored; there is no committed build. Deploy correctness rests on root `package.json` `build-pwa` running on Frappe Cloud. The local bundle (3 Sep) is behind 39 source files.
- Backend security sweep: no SQL string-building anywhere in `hrms/api`, `hrms/sync`, `hrms/hr/utils.py`; every `employee`-argument endpoint goes through `_ensure_own_employee_or_permitted`; `approval.decide/finalize` lock the row and always go through `doc.submit()/cancel()`; every sync endpoint is `only_for` + company-fenced (AST-tested). `allow_guest` endpoints: `oauth_providers`, `get_user_pass_login_disabled`, dev-only `get_context_for_dev` — no enumeration surface. Reset-password treats 200 and 404 alike.
- Frontend/backend contract: 61 `hrms.*` + 9 `frappe.*` method strings, ~90 call sites, all resolve to whitelisted defs with matching parameter names. All 45 routed components exist; no dead routes or views.
- Launcher patches (`rename_frappe_hr_desktop_icon`, `repair_nadi_desktop_icon_children`) are idempotent and ordered correctly; bench has 0 orphans and no "Frappe HR" row. `hooks.py` dotted paths all resolve; `patches.txt` lists every v16_0 patch file.
- Dev-site caveats: fresh.local is 3 patches behind `patches.txt`, scheduler disabled, 600 queued jobs (a `delete_doc` fails with QueueOverloaded). The 8 workspace-link and sidebar checks were unaffected.

## Suggested order

1. D1 + D2 (one commit each: icon roles + report timestamps/patch). Both are exposure.
2. F1 (fix the three e2e tests: two URLs, one CSRF header). This turns the approval regression test on for the first time.
3. F2 + the gate extension, then F3 minimum banner.
4. D3, D4, D5 (GATE 0 JSON fixes), then D6/D7 docs and Employee Advance wiring.
5. Update THE_PLAN: strike 3.1/3.3/3.5/3.6, replace 2.4's cache hypothesis with F1.

## Fix plan (written 7 Sep, after the audit)

One cause per commit. Every `fix:` ships with the test that goes red on HEAD.
After each commit the review hook runs; Nabil deploys on Frappe Cloud, which
runs `bench migrate`, so every Desk fix must land through JSON timestamps or a
patch, never a console command.

| # | Commit | Files | Red test |
|---|---|---|---|
| 1 | `fix(desk): role-gate the nine Nadi launcher children` — D1 | `hrms/desktop_icon/*.json` (+`roles`, bump `modified`) | `hrms/tests/test_desktop_icon_fixtures.py`: every child carries HR User / HR Manager / System Manager |
| 2 | `fix(desk): payroll deduction reports get their HR roles on live sites` — D2 | both report JSONs (bump `modified`), new `patches/v16_0/add_roles_to_payroll_deduction_reports.py`, `patches.txt` | `scripts/check_fixture_timestamps.py` exits 0; patch listed and idempotent (bench-free stub like `test_repair_nadi_desktop_icon_children.py`) |
| 3 | `test(e2e): critical paths aim at /dashboard/leaves and send the CSRF token` — F1 | `frontend/e2e/critical-paths.spec.js` | the suite itself: 6/6 against fresh.local |
| 4 | `fix(pwa): Home request panel says when a fetch failed` — F2 | `RequestPanel.vue`, `test_pwa_resource_states.py` (gate extension) | resource-states gate red on HEAD |
| 5 | `fix(desk): GATE 0 launcher JSON` — D3, D4 | `shift_&_attendance.json` sidebar (+Shift Assignment Tool), `hr_setup.json` (+Data Migration card block), `hr_outstanding.json` (+`modified`), new `desktop_icon/hr_outstanding.json` + sidebar | extend `test_hr_outstanding_workspace.py` and `test_workspace_access_gating.py` |
| 6 | `fix(desk): ship a standard HR Workspace Sidebar` — D5 | `hrms/workspace_sidebar/hr.json` | bench-free JSON shape test |
| 7 | `fix(api): doctype meta endpoints check read permission` — S1 | `hrms/api/__init__.py` | stub test: PermissionError for a doctype the caller cannot read |
| 8 | `docs: THE_PLAN strikes 3.1/3.3/3.5/3.6, 2.4 rewritten; role matrix regenerated` — D6, drift | `docs/glass/plan/THE_PLAN.md`, `reference/role-access-matrix.md` | none (docs) |
| 9 | `refactor(desk): unwire Employee Advance from HR pages` — D7 | `expenses.json`, `hr_setup.json`, `employee_advance.js` | JSON shape test |
| 10 | `feat(pwa): offline banner disables the punch` — F3 minimum | `CheckInPanel.vue` + unit test | node:test |

Minors (F5–F9, D8–D12, coherence C1) follow as `fix:`/`chore:` one-liners
once the above are deployed and verified on Verifica.

**Pipeline summary.** Requirements: this document. Planning agents: none
further (scope is fixed per row). Workspace: branch `nz-glass`, worktree
`/home/nabil/nz-version-16`. TDD: red test per row, then the change. Commit:
one per row, conventional message, hook-gated. Review: post-commit hook
dispatches `frappe-reviewer` / `code-reviewer`; Critical → fix and re-commit.
Deploy: push; Nabil deploys on Frappe Cloud; verify with the GATE 0 checklist
and `critical-paths.spec.js` against the live URL.
