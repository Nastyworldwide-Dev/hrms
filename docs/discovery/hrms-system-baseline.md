# HRMS System Baseline — Discovery Report

- **Date:** 2026-08-13
- **Branch:** `nz-version-16` @ `768792f65` (v16.19.0) — clean tree, no uncommitted work
- **Repo:** fork of `frappe/hrms` at `github.com/Nastyworldwide-Dev/hrms` (origin); this checkout is a git **worktree** (`.git` is a file)
- **Status legend:** claims are tagged **[Verified]** (code/config/tests), **[Inferred]** (strongly suggested), or **[Unknown]**
- *Location note: the repo had no `docs/` directory or documentation convention, so `docs/discovery/` was created as requested.*

---

## 1. Executive summary

This is **Frappe HR v16** (the open-source HRMS built on the Frappe framework + ERPNext) carrying a substantial custom layer that turns it into a **multi-company "HR hub"** for the Nastyworldwide group. The fork's defining program (commits `10e63ba8a` → `901e8b059`) is a **parallel-run migration architecture**: HR data (Employee, Attendance, Employee Checkin, Leave Ledger Entry) is **shadow-synced one-way** from source ERPNext instances into this hub (`hrms/sync/`), mirrored rows are made **read-only locally** by a single-writer write-block, and a **parity gate** plus a per-instance **cutover switch** govern when the hub takes over as the system of record.

On top of upstream HR/Payroll, the fork adds: layered **company/instance permission fencing** for multi-company HR staff, a hardened **"staff lockdown"** mobile API, **geofenced check-ins** with a remote-approval workflow, an **overtime → pay-or-replacement-leave** pipeline, an employee **helpdesk** (Employee Issue), an **SOP library**, KPI dashboards, and rule engines that auto-assign shifts and leave policies.

Quality posture is strong for a brownfield fork: 178 test files, security-review-driven commits (SEC-01…04 markers in code), semgrep rules for test correctness, CI that migrates a real v14 backup forward, and semantic-release on `version-16`. The riskiest areas to touch are `hrms/hooks.py` doc_events wiring, the sync/write-block subsystem, and the permission override layer — all have explicit invariants pinned by tests.

## 2. Product purpose and user personas

**Purpose** [Verified]: HR + Payroll management for a multi-company organization, with an employee-facing mobile PWA, while HR operations are consolidated from several source ERPNext instances into one hub during a phased migration ("parallel run", `hrms/sync/write_block.py:1-27`).

**Personas** (all backed by roles/permissions in code):

| Persona | Evidence | What they do |
|---|---|---|
| Employee (ESS) | `Employee Self Service` role profile (`hrms/setup.py:840`); PWA routes (`frontend/src/router/`) | Check in/out (geofenced), apply for leave/expense/OT/shift changes, view salary slips, file helpdesk issues, read SOPs |
| Approver (manager) | `leave_approver`, `shift_request_approver`, `reports_to` fields; `hrms/overrides/approval_row_scope.py` | Approve leave/expense/shift/remote-checkin requests routed to them |
| HR User / HR Manager | `HR_ROLES` bypass in row scopes; doctype perms | Full HR operations within their fence |
| HR (Company) | fence role (`hrms/utils/company_fence.py:43-47`) | HR for exactly one company (fenced via User Permissions) |
| HR (Instance) | fence role, R2 (`hrms/utils/company_fence.py`, patch `v16_0.add_hr_instance_fence_role`) | HR for the whole company-set of one source ERP instance (registry-driven) |
| HR Manager (Group) | `GROUP_HR_ROLE` — never fenced | Group-wide HR oversight |
| System Manager | break-glass in `write_block.py:87`; registry lock `hrms_erp_instance.py:53-85` | Admin, registry curation, cutover, break-glass repairs (audited) |
| Device/integration account | `add_log_based_on_employee_field` (`hrms/hr/doctype/employee_checkin/employee_checkin.py:133-160`) | Biometric punch ingestion (requires real `create` perm on Employee Checkin) |

## 3. Repository and technology overview

**Shape** [Verified]: modular monolith — one Frappe app (`hrms/`) installed into a bench site alongside `frappe` and `erpnext` (both `>=16.0.0,<17` — `pyproject.toml:83-85`), plus two embedded Vue SPAs and a git submodule.

| Component | Path | Stack |
|---|---|---|
| Backend app | `hrms/` | Python ≥3.10, Frappe v16, ERPNext v16, MariaDB, Redis |
| ESS PWA | `frontend/` | Vue 3.5, Ionic 7, Tailwind, Vite, frappe-ui, Firebase (push), workbox |
| Shift roster SPA | `roster/` | Vue 3, frappe-ui, Vite |
| Shared UI lib | `frappe-ui/` | git submodule (`.gitmodules`) |
| Dev container | `docker/docker-compose.yml` | MariaDB 10.8, Redis, bench container, ports 8000/9000 |
| CI/release | `.github/workflows/`, `.releaserc`, `.mergify.yml`, `commitlint.config.js` | GH Actions, semantic-release (branch `version-16`), mergify |
| Lint | `.pre-commit-config.yaml`, `pyproject.toml [tool.ruff]`, `semgrep/` | ruff (line 110, tabs), prettier, custom semgrep |

Two Frappe modules only: **HR** and **Payroll** (`hrms/modules.txt`). Branches: `version-15` (previous line), `version-16` (current line, contains all custom work — `git merge-base HEAD origin/version-16` == HEAD).

## 4. Runtime and architecture map

```
                 ┌──────────────── Bench site (Frappe v16) ───────────────────┐
 Employee ──────▶│ /hrms  ESS PWA (Vue/Ionic)  ──┐                            │
 (mobile/web)    │ /hr/roster  Roster SPA ───────┤ frappe-ui resourceFetcher  │
                 │ /app  Frappe Desk (HR staff) ─┤ (session cookie auth)      │
                 │                               ▼                            │
                 │  hrms/api/*  whitelisted API (staff lockdown)              │
                 │  DocType controllers + doc_events hooks (hrms/hooks.py)    │
                 │  Permission layer: roles + User Permissions + row scopes   │
                 │  Scheduler jobs (hooks.py:351-391)   socketio (realtime)   │
                 │  MariaDB (one DB per site)     Redis (queue/cache)         │
                 └───────────────▲──────────────────────────────┬─────────────┘
                                 │ one-way GET-only pull        │ FCM push, email,
     Source ERPNext instances ───┘ (hrms/sync/client.py,        │ PostHog telemetry
     (HRMS ERP Instance registry)   token auth, mirrored rows   ▼
      biometric devices ──▶ add_log_based_on_employee_field  external services
```

- **Entry points** [Verified]: Desk UI (`/app`, `app_home=/desk/people`), ESS PWA served at `/hrms` (`hrms/www/hrms.py`, `website_route_rules` in `hooks.py:82-85`), roster at `/hr/roster` (`hrms/www/roster.py`), whitelisted RPC under `hrms.api.*`, doc events, scheduler, and the biometric ingestion endpoint.
- **Realtime** [Verified]: controllers publish `hrms:refetch_resource` (e.g. `leave_application.py:157-160`); PWA listens via socket.io (`frontend/src/socket.js`).
- **Failure behavior**: sync runs are per-doctype contained with `Partial` status and an `HRMS Sync Run` audit row (`hrms/sync/runner.py`); fence reconciliation is per-user contained (`company_fence.py:212-259`); shift-rule sweeps use per-employee savepoints (`hrms/hr/shift_rules.py`).

## 5. Module ownership table

| Subsystem | Lives in | Purpose / notes |
|---|---|---|
| Leave management | `hrms/hr/doctype/leave_*`, `leave_rules.py` | Allocation, application, ledger, policies; grade-driven auto policy assignment (daily job) |
| Attendance & shifts | `hrms/hr/doctype/{attendance*,shift_*,employee_checkin}`, `shift_rules.py` | Auto-attendance from checkins (hourly_long), location/department-driven auto shift assignment, shift schedules, swaps |
| Geofenced check-in (custom) | `hrms/api/{geofence,remote_checkin}.py`, `hrms/overrides/employee_checkin_*`, `remote_checkin_request` doctype, `hrms/utils/checkin_sweeper.py` | Strict geofence preflight/insert block; lenient mode → Remote Checkin Request approval; stale-IN sweeper (10:00 cron) |
| Overtime (custom) | `ot_request`, `overtime_slip`, `overtime_type`, `replacement_leave_claim` doctypes | Punch-verified OT; pay route via Overtime Slip → Additional Salary; leave route via Replacement Leave Claim → allocation |
| Expense claims | `hrms/hr/doctype/expense_claim*`, ERPNext GL hooks (`hooks.py:237-259`) | Claims/advances with accounting integration |
| Recruitment | `job_*`, `interview*` doctypes | Openings (website generator), applicants, offers, interviews |
| Performance | `appraisal*`, `kpi`, `goal`, custom `appraisal_b4/b5_evidence`, `leadership_scorecard` | Custom-extended appraisal scoring (see `.claude/plans/appraisal-achievement-scoring.md` — planned change) |
| Lifecycle | `employee_onboarding*`, `employee_separation*`, `full_and_final_*`, boarding controller | Onboarding/exit via Project+Task automation |
| Helpdesk (custom) | `employee_issue` doctype + `overrides/employee_issue_row_scope.py` | Private employee↔HR tickets; HR-managed status |
| SOP library (custom) | `sop_document` doctype, `hrms/api/sop.py`, `overrides/sop_document_row_scope.py` | Published SOPs scoped General/department; S3 presigned attachment support |
| Payroll | `hrms/payroll/` | Salary structures/slips, payroll entry, income tax, withholding, gratuity, benefits |
| Regional | `hrms/regional/{india,china,malaysia,united_arab_emirates}` | India HRA/tax/marginal-relief overrides (`hooks.py:420-426`); others minimal |
| **Sync / HR hub (custom)** | `hrms/sync/`, `hrms_erp_instance*`, `hrms_sync_run` doctypes | Registry, one-way shadow sync, write-block, company shells, parity gate |
| **Permission fencing (custom)** | `hrms/overrides/*_scope.py`, `hrms/utils/company_fence.py` | Row scopes, company/instance fences, ESS User-Permission sync |
| Mobile API | `hrms/api/` | PWA backend, staff lockdown guard |
| Telemetry | `hrms/telemetry.py` | Product usage/activation events via `frappe.utils.telemetry` (PostHog) |

## 6. Core data model and systems of record

- **Employee** is the axis of everything; ERPNext's doctype overridden by `hrms.overrides.employee_master.EmployeeMaster` with fork-added fields (shift_location, ot-pay eligibility, years_of_service, interco allocation, notice period unit — see `hrms/patches.txt`).
- **Leave state** = Leave Allocation + **Leave Ledger Entry** (append-only ledger; applications/encashments/expiry write entries).
- **Attendance** derives from **Employee Checkin** via Shift Type auto-attendance (hourly_long job, `hooks.py:359-361`).
- **Payroll** = Salary Structure/Assignment → Salary Slip ← Payroll Entry; OT feeds in via Overtime Slip → Additional Salary [Verified, agent-traced: no direct OT→payroll coupling].

**Systems of record — the critical fork twist** [Verified]:

| Data | SoR while a company is in the parallel run | SoR after cutover |
|---|---|---|
| Employee, Attendance, Employee Checkin, Leave Ledger Entry (rows stamped `synced_from_instance`) | **Source ERPNext instance** — local rows are read-only mirrors (`hrms/sync/write_block.py:42-47`) | This hub (per-instance `unlock_mirrored_writes` flips writing rights) |
| Company | Created locally as **shells** from registry (`hrms/sync/company_shells.py`), never stamped, create-only | Hub |
| Everything else (leave applications, expenses, OT, payroll, appraisal, …) | Hub | Hub |

Mirrors are **name-keyed idempotent upserts, incremental by `modified >` watermark, never deleted**; per-row referential integrity skips orphans (`hrms/sync/runner.py`, pinned by `hrms/tests/test_sync_runner.py`). `hrms/sync/parity.py` counts stamped rows vs remote as the cutover-readiness gate.

## 7. Authentication, permissions, and data-isolation model

**Authentication** [Verified]: standard Frappe session cookies; PWA login screen supports social OAuth (`hrms/api/oauth.py` — the only two `allow_guest` endpoints are login-screen support: `oauth_providers` and `get_user_pass_login_disabled`; neither returns secrets). No custom `auth_hooks`.

**Authorization is enforced server-side, in four stacked layers** (the UI is not a boundary):

1. **Role/doctype permissions** (doctype JSONs; `permlevel 1` protects registry credentials + cutover switch — `hrms_erp_instance.json`).
2. **Row scopes** via `permission_query_conditions` + `has_permission` for 13 doctypes (`hooks.py:145-192`): approver-routed docs (Leave Application, Expense Claim, Shift Request) grant own+approver+shared+HR (`overrides/approval_row_scope.py`); OT docs grant own+direct-reports+HR (fail-closed); Employee Issue is private employee↔HR; SOP visibility is published+General/own-department; Appraisal is own-only for employees. Design note in hooks.py: row scope deliberately lives in these hooks, *not* in per-employee User Permissions, which would 403 approvers (patch `v15_101_0.drop_approval_doctype_user_permissions`).
3. **Company/instance fences** (`overrides/company_scope.py`, `utils/company_fence.py`): an `allow=Company` User Permission narrows Employee visibility; `HR (Company)` gets one company, `HR (Instance)` gets the registry-driven set of its source instance. **Users with no Company UP are unrestricted (fail-open by design, for backward compatibility)** — a nightly job reconciles fences and reports unfenced HR users into Error Log (`company_fence.py:262-294`, wired at `hooks.py:376`).
4. **Mobile API "staff lockdown"** (`hrms/api/__init__.py:154-167`): every employee-parameterized endpoint calls `_ensure_own_employee_or_permitted` (19 call sites) — own record or real Employee read permission, otherwise fail-closed with a logged denial. `punch` additionally enforces self-only check-in (`api/remote_checkin.py:252`); approvals verify the assigned approver (`_ensure_approver`). Roster mutations check document-level `check_permission` before any `ignore_permissions` deletes (`api/roster.py:182,189`).

**Single-writer write-block** [Verified, `hrms/sync/write_block.py`]: every write path (validate, update-after-submit, cancel, trash, **rename**) on mirrored doctypes is guarded (`hooks.py:261-324`). Escape hatches in precedence: sync flag → migrate/patch/install → per-instance cutover unlock → System Manager break-glass (logged to server log **and** Error Log for Desk-visible audit; renames get *no* break-glass, SEC-01). Provenance stamps can be neither stripped nor forged (SEC-03). Known residual: `frappe.db.set_value` bypasses doc events; the one audited writer (`utils/checkin_sweeper.py`) excludes mirrored rows at the query, pinned by `test_write_block.py`.

**Registry as permission boundary** [Verified]: only System Manager may edit an instance's companies table (`hrms_erp_instance.py:53-85`, commit `901e8b059`) because it drives fence provisioning; company-shell endpoints are `only_for(System Manager, HR Manager)` + unfenced-operator check + POST-only + max 50/run.

**ESS User-Permission scoping** [Verified]: `restrict_user_permission_to_hrms` on Employee creates one UP per HRMS-scoped doctype (~16) instead of a broad anchor; ordering vs ERPNext's controller is load-bearing (`hooks.py:271-282`, `overrides/employee_hrms_scope.py`).

**Audit trails**: standard Frappe versioning/Error Log; break-glass writes create Error Log entries; sync runs persist `HRMS Sync Run` records; API denials and geofence decisions are logged to the `hrms` logger. **PII/retention**: `user_data_fields` (GDPR redaction hook) is commented out (`hooks.py:465-487`) — no in-app redaction/retention policy [Verified absent]. Credentials: remote API secret is a Password field (encrypted at rest), with a **legacy plaintext fallback in site config** (`sync/client.py:152-200`) [Verified].

## 8. Critical workflow traces

### 8.1 Leave application (ESS → approval → ledger)

1. **Trigger**: employee opens `/hrms/leave-applications` (PWA route) → reads via `hrms.api.get_leave_applications` / `get_leave_balance_map` (both behind `_ensure_own_employee_or_permitted`, `api/__init__.py:479-612`); creates a draft Leave Application document.
2. **Validation** (`hr/doctype/leave_application/leave_application.py:79-97`): active employee, date sanity, balance, overlap, max days, block days, salary-processed days, attendance conflicts, optional-leave rules, `applicable_after` tenure, **self-approval prevention** (`validate_for_self_approval:912`), mandatory approver (`validate_leave_approver:898`, patch `v16_0.set_leave_approver_name_in_leave_application`).
3. **Routing**: `on_update` shares the doc with the approver (`share_doc_with_approver:108`) and notifies (`notify_leave_approver:717`); row scope makes it visible to owner+approver+HR only (`overrides/approval_row_scope.py`).
4. **Approval**: approver sets status Approved and submits; `on_submit:112-137` blocks non-Approved/Rejected submits, updates Attendance (`update_attendance:117`), writes **Leave Ledger Entry** (`create_leave_ledger_entry:767`), adds an expiry-reversal entry for backdated applications on expired allocations.
5. **Side effects**: employee notification (HR Settings-gated), realtime `hrms:refetch_resource` push (`publish_update:157-160`), telemetry event (`hooks.py:331`).
6. **Cancel**: reverse ledger entry + attendance cancel (`on_cancel:145-152`).
7. **Failure/tests**: everything throws inside the transaction (no partial state); covered by upstream leave tests + `test_staff_lockdown.py`, `test_approval_row_scope.py`.

### 8.2 Geofenced check-in with remote approval (custom)

1. **Trigger**: PWA check-in button → **preflight** `hrms.api.geofence.check_geofence` (`api/geofence.py:61-172`): company-level rollout flag, resolves the active Shift Assignment as of the *employee's* wall clock, and if `enable_strict_geofence` (moved to Shift Assignment in v15.77.4) computes distance vs `Shift Location.checkin_radius` → returns `strict_block` or ok.
2. **Punch**: `hrms.api.remote_checkin.punch` (`remote_checkin.py:230-293`) — **self-only** (throws unless session user owns the employee), validates selfie attachment ownership, inserts Employee Checkin.
3. **Insert path**: `CustomEmployeeCheckin` override (`overrides/employee_checkin_override.py`) picks the correct shift among staggered shifts, re-evaluates the geofence; strict violations throw `CheckinRadiusExceededError` (`employee_checkin.py:96-130`); lenient out-of-radius sets `requires_remote_approval`.
4. **Remote approval**: `after_insert` creates a **Remote Checkin Request** (`overrides/employee_checkin_after_insert.py:18-93`; OUT logs inherit the day's approved IN request unless late checkout). Approver resolution chain: `shift_request_approver` → department approver → `reports_to` → any HR Manager (`overrides/remote_checkin_request_hooks.py:23-104`). Approver acts via `approve`/`reject` (assigned-approver-only, `remote_checkin.py:44-64`); `propagate_approval_decision` (`hooks.py:325-327`) stamps the decision back onto the checkin and notifies via PWA notification, email, push, and socket.
5. **Background**: hourly_long auto-attendance converts checkins to Attendance (`hooks.py:359-361`); 10:00 cron sweeps stale INs with no OUT within 36h (`utils/checkin_sweeper.py`, mirrored rows excluded).
6. **Tests**: `overrides/test_remote_checkin_request_hooks.py` (approver chain), `hr/doctype/employee_checkin/test_employee_checkin.py`, `tests/test_checkin_timezone.py`. Gap: no dedicated test for the OUT-inheritance path [Verified gap per sweep].

### 8.3 Shadow sync run and cutover (the fork's core)

1. **Trigger**: `hrms.sync.runner.run_sync` — whitelisted, `frappe.only_for(("System Manager","HR Manager"))`. No scheduler wiring: **sync is operator-initiated** [Verified — absent from `scheduler_events`].
2. **Fetch**: `RemoteInstanceClient` (`sync/client.py`) — GET-only by construction (refuses other verbs), token auth from the registry record (Password field; legacy site-config fallback), paginated (500/page), 3 retries on 5xx/timeouts, secrets never logged.
3. **Write**: dependency-ordered (Company shells → Employee → Attendance/Checkin/Leave Ledger), per-row referential-integrity skips, idempotent name-keyed upserts, `synced_from_instance` stamped, `frappe.flags.in_shadow_sync` marks the sync as the one legitimate writer; a doctype whose prerequisite failed is not synced (`966047310`).
4. **Audit**: `HRMS Sync Run` record with status Running/Completed/Failed/Partial + row counts + error log.
5. **Enforcement between runs**: write-block (see §7) makes mirrored rows read-only for everyone below System Manager; renames blocked for all.
6. **Cutover**: `parity.py` compares stamped-row counts vs remote per doctype and tracks consecutive clean runs; a human flips `unlock_mirrored_writes` (permlevel 1) per instance.
7. **Tests**: `tests/test_sync_runner.py`, `test_sync_client.py`, `test_sync_parity.py`, `test_write_block.py` (including AST checks that hooks wiring never drops a guard), `test_company_shells.py` (payload/AST/endpoint hardening), `test_erp_instance_*`.

### 8.4 Overtime → pay or replacement leave (custom)

1. **Trigger**: employee files **OT Request** (PWA `/ot-requests`; reads behind staff lockdown, `api/__init__.py:289-388`).
2. **Rules** (`hr/doctype/ot_request/ot_request.py`): same-month filing only, requested hours capped by punch-verified checkin/checkout vs shift end, one request per employee per date; compensation route (Overtime Pay vs Replacement Leave) forced read-only from `Employee.eligible_for_overtime_pay`.
3. **Pay route**: Overtime Slip computes amounts and creates **Additional Salary** rows consumed by the next Salary Slip (payroll is otherwise decoupled from OT).
4. **Leave route**: **Replacement Leave Claim** converts hours in 4-hour half-day steps into a Replacement Leave allocation + ledger entry; bank month is server-controlled; cancel reverses allocation and is blocked if hours were already consumed.
5. **Access**: no approver field — submission is the approval; row scope = own + direct reports + HR (`overrides/ot_row_scope.py`, fail-closed).
6. **Tests**: `test_ot_request.py`, `test_overtime_slip.py`; row scope itself has no dedicated test [gap].

## 9. Integrations and background processing

**External integrations** [Verified]:
- Source ERPNext instances — sync (GET-only token auth) + "Open my ERP" deep link (`hrms/api/erp_instance.py`).
- Biometric devices — `add_log_based_on_employee_field` (requires real create permission; allowlisted lookup fields).
- Firebase Cloud Messaging — PWA push via Frappe's push-relay (`are_push_notifications_enabled`, `frontend/src/main.js`).
- PostHog product telemetry via `frappe.utils.telemetry` (`hrms/telemetry.py` — usage + activation-funnel events; site-level opt-out governed by framework).
- S3 presigned URLs for SOP attachments (`hrms/api/sop.py:202`).
- Employment Hero — settings doctype exists (`employment_hero_settings`) [Inferred: integration scope unverified].
- Email/SMTP, socket.io realtime — framework-standard.

**Scheduler jobs** (`hooks.py:351-391`): interview reminders (all/daily), daily-work-summary (hourly), **auto-attendance + checkin sync + auto shift creation (hourly_long)**, daily: shift-rule reconciliation, auto leave policies, years-of-service sweep, birthday/anniversary reminders, expired shift assignments/job openings, attendance-pulse telemetry, **fence hygiene**; 10:00 cron stale-IN sweeper; daily_long: leave-allocation expiry, encashment, earned-leave accrual. Background jobs run via Redis queues (bench workers) [Inferred from framework].

## 10. Local development and verification commands

From `README.md:77-107` and CI [Verified as documented; not all executable in this checkout]:

```sh
# Docker route
cd docker && docker-compose up          # site at http://localhost:8000 (Administrator/admin)

# Bench route
bench start
bench new-site hrms.local && bench get-app erpnext && bench get-app hrms
bench --site hrms.local install-app hrms

# Tests (as CI runs them, needs a bench + test_site)
bench --site test_site run-parallel-tests --app hrms --lightmode

# Some fork tests are bench-free "file mode" (mocked frappe) — still need
# frappe importable in the venv (see note below)

# Lint
pre-commit run --all-files              # ruff + prettier + hygiene hooks
ruff check .

# Frontends
cd frontend && yarn dev                 # PWA (proxies to :8000)
cd roster && yarn dev
```

**Commands run during this discovery** (all read-only): git inspection (`status`, `branch`, `log`, `merge-base`, `diff --stat`), file reads/greps, and one test attempt: `python3 -m unittest hrms.tests.test_write_block` → **failed: `ModuleNotFoundError: No module named 'frappe'`** — this worktree is not attached to a bench virtualenv, so no Python tests can run here. Recorded rather than altering the environment. No code, config, or dependency was modified; the only file created is this report.

## 11. Testing, CI/CD, deployment, and observability

- **Tests** [Verified]: 178 `test_*.py` files. Fork-critical suites: `hrms/tests/test_sync_*.py` (runner/client/parity/provenance), `test_write_block.py` (decision table + AST wiring checks + set_value-bypass pin), `test_company_{fence,shells,api_scope,settings}.py`, `test_staff_lockdown*.py`, `overrides/test_*.py`, plus doctype suites for OT, checkin, issues, SOPs, shift/leave rules.
- **CI** (`.github/workflows/`): `ci.yml` — 3-way parallel unit tests on MariaDB 11.8, Python 3.14/Node 24, codecov upload; `linters.yml` — commitlint + pre-commit + semgrep (frappe rules + custom `semgrep/test-correctness.yml` banning `db.commit()`/`truncate()`/`tearDown` overrides in tests); `patch.yml` — restores a v14 backup and migrates v15→v16 across Python 3.11/3.13/3.14 (real migration safety gate).
- **Release**: semantic-release on `version-16` (`.releaserc` — breaking changes deliberately blocked from releasing), conventional commits enforced, mergify auto-merge/backport rules.
- **Deployment** [Unknown]: no production infra in the repo (docker/ is dev-only). Frappe-standard options (bench on VM, Frappe Cloud, containers) — actual environment/process is outside this repo. `build_image.yml` exists for image builds.
- **Feature flags/rollout** [Verified pattern]: per-company setting overrides (`is_company_setting_enabled`, patch `add_company_hr_policy_overrides`) gate geolocation rollout company-by-company; per-instance cutover switch; HR Settings toggles.
- **Observability** [Verified in-repo]: `frappe.logger("hrms")` + module loggers across custom code (sync, fence, geofence, API denials); Error Log records for break-glass and unfenced-HR reports; `HRMS Sync Run` audit doctype. No Sentry/APM config in-repo [Unknown at site level].
- **Backup/rollback** [Inferred]: framework-level (`bench backup`, patch idempotency); `patch.yml` proves forward-migration; no rollback tooling in-repo.

## 12. Risk register (P0–P3)

**No P0 (exploitable security/data-loss) issue was found.** Confirmed vs suspected is marked per row.

| # | Sev | Status | Risk | Evidence | Impact / containment |
|---|---|---|---|---|---|
| R1 | **P1** | Confirmed (deliberate design) | **Fail-open company fence**: any HR User/Manager with no fence role and no `allow=Company` UP sees *all* companies' employee data | `overrides/company_scope.py` (no-op without UP); `company_fence.py:262-288` nightly report | Cross-company PII exposure if onboarding forgets the fence role. Mitigation exists (nightly Error Log report) but is detective, not preventive. Decide: flip to fail-closed post-migration, or make fence roles mandatory in onboarding SOP |
| R2 | **P1** | Suspected (hypothesis) | **Dual-writer leave state for mirrored companies**: Leave Application is *not* a mirrored doctype; a hub-side approval writes an *unstamped* Leave Ledger Entry next to mirrored ones → silent divergence from source, and parity (which counts only stamped rows) won't see it | `write_block.py:42-47` (mirrored list), `leave_application.py:767`, `sync/parity.py` | Needs product confirmation of the operating rule "staff of mirrored companies transact only on the source instance". If that rule is policy-only, consider blocking hub-side leave/attendance-writing transactions for employees whose Employee row is stamped |
| R3 | P2 | Confirmed (documented residual) | `frappe.db.set_value`/raw-SQL writers bypass the write-block by construction; only one audited writer today | `write_block.py:23-26` docstring; `test_write_block.py` TestSetValueWriters | Future code can silently violate single-writer. Add a review checklist rule / semgrep rule for `set_value` on mirrored doctypes |
| R4 | P2 | Confirmed | System Manager break-glass can edit mirrored rows (audited, stamp-preserving, renames excluded) — powerful and routine-looking in Desk | `write_block.py:87,159-174` | Acceptable by design; ensure System Manager role assignment stays minimal; monitor Error Log for overrides |
| R5 | P2 | Confirmed | Legacy plaintext sync credentials fallback in `site_config.json` | `sync/client.py:152-200` | Anyone with site-config/file access reads remote read-only API keys. Migrate remaining site-config credentials into the registry doctype and delete the fallback |
| R6 | P2 | Confirmed | No PII redaction/retention config: `user_data_fields` commented out; mirrored rows multiply PII copies across hub + sources | `hooks.py:465-487` | GDPR/PDPA data-subject requests need a defined path; exports via report/PDF endpoints are permission-gated but unredacted |
| R7 | P3 | Confirmed | `check_geofence` has no ownership check on `employee`: any authenticated user can probe another employee's shift existence/type/location name and distance-to-location from chosen coordinates (allows trilaterating site coordinates) | `api/geofence.py:61-172` | Low sensitivity (work-site config, not personal location), inconsistent with the staff-lockdown pattern; one-line fix candidate |
| R8 | P3 | Confirmed | Row-scope override tests missing for `ot_row_scope`, `employee_issue_row_scope`, `sop_document_row_scope`; no test for OUT-checkin approval inheritance | test sweep (§11) | Regression risk in the exact layer that guards privacy |
| R9 | P3 | Confirmed | `hooks.py` doc_events is a hand-maintained dict where a duplicate key silently drops handlers — already bit the v16 port once | `hooks.py:297-299` comment; AST test pins it | Any hooks edit must run `test_write_block.py` (wiring checks) |
| R10 | P3 | Confirmed | Heavy fork divergence from upstream `frappe/hrms` (ports done by hand: `chore(v16): port ...` series) | git history | Upstream merges are non-trivial; budget for conflict-heavy rebases each major version |

## 13. Verified facts, inferences, and unknowns

**Verified** (direct evidence): everything tagged [Verified] above — fork lineage and phases (git log), module inventory, permission layers and their exact bypass roles, write-block decision table, sync mechanics (direction, idempotency, watermark, provenance), staff-lockdown coverage (19 call sites), CI/test/release setup, scheduler jobs, the two allow_guest endpoints, roster endpoint permission checks (`api/roster.py:182,189`), `_download_pdf` delegating to framework permission-checked `download_pdf`.

**Inferred** (strong signal, not explicit): the business is a multi-company group consolidating several ERPNext-based companies into one HR hub ("Nastyworldwide", instance example "nasty-live" in code); staff of mirrored companies are expected to transact on their source instance during the parallel run; production runs on a Frappe bench-style deployment; background jobs run via Redis workers.

**Unknown** (not determinable from the repo): production topology, environments, backup/DR practice; which companies/instances are currently registered and how far the parallel run has progressed; whether telemetry is enabled in production; SLAs for sync freshness; Employment Hero integration status; the intended post-cutover decommissioning plan for `hrms/sync`; whether the appraisal-scoring plan (`.claude/plans/appraisal-achievement-scoring.md`) is approved work.

## 14. Questions for stakeholders

**Product**: Is the operating rule during the parallel run that mirrored-company staff use only their source ERP for leave/attendance (see R2)? What is the cutover schedule per instance? Is the appraisal achievement-scoring change (plan file) approved and prioritized?

**Engineering**: Should the company fence become fail-closed once migration completes (R1)? Is there appetite for a semgrep rule banning `db.set_value` on mirrored doctypes (R3)? Who owns upstream-merge cadence with `frappe/hrms` (R10)?

**Security**: Should `check_geofence` adopt `_ensure_own_employee_or_permitted` (R7)? Are any sync credentials still living in `site_config.json` (R5)? Who reviews Error Log break-glass overrides and unfenced-HR reports, and how often?

**Data/Privacy**: What is the DSAR/retention story given `user_data_fields` is unconfigured and PII is duplicated across hub + source instances (R6)? Is PostHog telemetry enabled in production, and is that disclosed?

**Operations**: Where does production run, and what are its backup/rollback procedures? Is `run_sync` operator-run on a cadence, or should it be scheduled with alerting on `Partial`/`Failed` HRMS Sync Run records? Who is paged when nightly fence hygiene reports unfenced users?

## 15. Recommended next discovery steps

1. Get read access to a staging/production site config and one registered instance to confirm parallel-run state, sync cadence, and credential storage (R5).
2. Run the full test suite inside a bench (`bench --site test_site run-parallel-tests --app hrms --lightmode`) to establish a green baseline before any change.
3. Resolve R2 with product: trace whether any hub-side transaction can mutate leave/attendance state for a stamped employee, and pin the answer with a test.
4. Author the missing row-scope tests (R8) before touching the overrides layer.
5. Map the upstream delta (`git diff` against the matching `frappe/hrms` release tag) to quantify merge exposure (R10).

## 16. Readiness assessment

**Ready for scoped feature/bug-fix work**, with guardrails. The codebase is coherent, convention-driven (Frappe idioms + fork-specific invariants), and unusually well-pinned by tests in exactly the dangerous places. Before changing anything, an engineer must know:

- **Never edit `hooks.py` doc_events casually** — duplicate keys silently drop handlers; handler *order* on Employee is load-bearing (`hooks.py:261-296`); run `test_write_block.py` after any hooks change.
- **Mirrored doctypes are read-only by design** — do not "fix" PermissionErrors on stamped rows by adding bypasses; the write-block is a program invariant (R3/R4).
- **New whitelisted endpoints must self-enforce permissions** — the codebase's own rule (`api/sop.py:8`); follow the `_ensure_own_employee_or_permitted` pattern.
- **Permission changes ripple** — row scopes, fences, and ESS UP-sync interact; consult §7 before altering any of the three.
- **Commit style is enforced** (commitlint + semantic-release); tests run via bench, some fork suites also in file mode; CI includes a real v14→v16 migration gate, so patches must be idempotent.

Blocking unknowns for *implementation* work: none for hub-local features; anything touching sync/cutover or cross-company visibility needs the R1/R2 product answers first.
