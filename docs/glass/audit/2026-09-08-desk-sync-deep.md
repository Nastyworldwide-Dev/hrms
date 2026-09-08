# Desk, reports and mirror ownership — deep audit, 8 September 2026

Audit at `3ead59787`. Read-only application work: no source fixes, permission changes, data repair, commit or deployment. Only this report and synthetic audit probes were written. This extends the 7 September audit and the 8 September attendance/OT audit; repeated findings are explicitly labelled.

## New findings

### DS1 — High, conditional: Desk Script Reports can lose the app's company fence

The application deliberately treats a Company User Permission as a global HR company fence even when its `applicable_for` names a different doctype: `hrms/overrides/company_scope.py:19–28,54` and its canonical `hrms/utils/company_scope.py` implementation. The normal Employee/form/API paths honor that stronger rule.

Salary Register's SQL does not call that helper. `hrms/payroll/report/salary_register/salary_register.py:282–314` applies only caller-supplied filters. Its report roles include HR User and HR Manager.

**Framework correction:** the earlier claim that Script Reports receive no User Permission filtering is too broad. Installed Frappe `frappe/desk/query_report.py:121,894–940` post-filters result rows; `get_user_match_filters` calls `reportview.build_match_conditions(..., False)`. However, `frappe/database/query.py:1687–1722` includes only User Permissions applicable to the current linked doctype. It does not apply the application's stronger global company fence or its row-scope hook.

**Executed boundary reproduction:** synthetic Company permission permits COMPANY-ALLOWED but has `applicable_for='Leave Application'`. The actual installed Engine method returns **no match filter** for Employee. The Salary Slip and Company link paths have the same mismatch when the permission is scoped to Leave Application. Salary Register with an omitted or arbitrary company filter therefore has no application company predicate and no effective matching framework company filter in this configuration. Frappe's filter validation depends on Report filter metadata or the client-supplied `js_filters`; omitting client metadata is not a security boundary (`query_report.py:1131–1163`).

This demonstrates a boundary mismatch, not an observed production payroll disclosure. An authenticated company-fenced test account and synthetic payroll rows are still needed to replay the full report endpoint. Ordinary broad Company User Permissions can still filter report rows correctly; do not report every report as universally exposed.

**Correction:** apply the canonical permitted-company set in sensitive report queries before selection or aggregation, regardless of supplied filters. Audit siblings by actual query behavior, not the presence of a marker string. Preserve standard User Permission filtering as an additional check. Test restricted, unrestricted, other-doctype-scoped and multi-company HR across report view, export and prepared report paths.

### DS2 — Medium; High if used across a permission boundary: attendance report charts use rows hidden from the result grid

Installed `frappe/desk/query_report.py:121–142` filters only `result`. The separately returned `chart` and `report_summary` stay untouched. Monthly Attendance Sheet creates its attendance map from its own SQL (`monthly_attendance_sheet.py:313–363`) and chart from that whole map (`:758–803`). Neither applies the application's company/employee fence before aggregation.

**Executed boundary reproduction:** actual `generate_report_result` receives two synthetic attendance rows and a chart count of two. Its row-filter collaborator removes the hidden row. Returned grid length is **1**, returned chart count remains **2**. This probe isolates the framework boundary; it does not pretend to be an authenticated report execution.

A concrete affected configuration is a report allowed to query a parent company and descendants, while the HR user's Company permission allows only part of that set. Row postfiltering can remove hidden employees while chart totals still disclose their attendance counts. Department/Employee restrictions have the same class of risk. This is aggregate disclosure and misleading reporting, not proof of leaked employee identities.

**Correction:** build the map, grid, chart and summary from the same authorized population. Do not remove the chart or weaken row filtering to make counts agree. Verify grouped rows, multiple shifts, report exports and prepared results. Also inspect Employee Analytics: its per-category count uses `build_qb_match_conditions`, but its `Not Set` remainder uses unscoped `frappe.db.count` (`employee_analytics.py:85–99`); that is a sibling candidate needing its own role/data replay.

### DS3 — Medium: Half Day disappears from the Desk attendance chart

`monthly_attendance_sheet.py:318–330` converts Half Day into `Half Day/Other Half Present` or `Half Day/Other Half Absent`. The grid recognizes both. `get_chart_data`, `:781–783`, matches only literal `Half Day`.

**Executed reproduction:** one synthetic employee with either converted status produces zero in **all three chart series**. Both assertions fail. The issue affects the Desk report chart, independently of Nadi calendar generation.

**Correction:** calculate present/absent/leave fractions from the complete attendance status rather than comparing incompatible display labels. Pin both Half Day variants, ordinary Present/Absent/Leave and multiple shifts. The exact expected split must follow attendance semantics; the probe currently asserts only that a worked Half Day cannot disappear entirely.

The chart branch traces to inherited 2022–23 code. It was not changed by Hafiz's `e5acad89c..d050fa74b` range.

### DS4 — High, conditional data loss: releasing a mirror stamp does not protect a local RL grant

`hrms/hr/utils.py:705–725` deliberately tops up a mirrored Leave Allocation using `db_set`, bypassing document-event single-writer guards. Its comment says the manual workflow will not re-pull those employees, and recommends releasing the stamp before a full re-pull so the source cannot reclaim the allocation.

That proposed safeguard is incorrect. `hrms/sync/runner.py:923–924` explicitly allows an unstamped existing row to be claimed; `_write_row`, `:957–980`, overwrites its fields and restores source provenance. The real purpose of `release_instance_stamp`, documented in `hrms/sync/purge.py:157–177`, is precisely to let a later source reclaim rows.

**Executed reproduction:** synthetic allocation has a local RL top-up, total 3 days, and released stamp. Actual `_write_row` receives the source's older 2-day allocation. Result is **2 days**, stamped to the source again. A same-source stamped allocation is also eligible for overwrite by the same predicate. Neither release nor the instance's local-write unlock provides a pull exclusion in this path.

The risk is conditional on a later pull containing that allocation. An ordinary source modification followed by an incremental pull can also enter the same update path; it is not exclusive to a full pull. This audit did not run any sync, release or grant against a site.

**Correction:** define enforceable ownership before changing payroll/leave logic: exclude transferred rows from source updates, separate immutable source balances from explicit hub adjustments, or perform an actual controlled cutover that prevents later source pulls. Reconcile allocation totals and ledger deltas together; protecting only the allocation total can leave the ledger inconsistent. Correct the misleading operational comment immediately in the eventual reviewed slice. The older write-block comment still describes OT as writing a hub-native bank (`write_block.py:155–161`), which no longer matches per-day allocation grants.

Per-day grant implementation is `3fe56575f` (4 September); misleading mitigation comment is `8963f6200` (5 September). Neither changed in the latest Hafiz range. This is a documented architectural shortcut with a disproven mitigation, not evidence that Hafiz introduced the risk in the latest handoff.

### DS5 — Medium: a late Desk permission response replaces Save and can approve old values

The shared Desk helper requests `can_decide` on refresh (`hrms/public/js/utils/request_approval.js:45–66`). It checks dirty state before the request, but its asynchronous callback checks only permission and docstatus before replacing the primary action with Approve.

**Executed reproduction:** open a saved OT draft; delay `can_decide`; HR edits the form; Frappe's dirty handler restores Save (`frappe/public/js/frappe/form/toolbar.js:850–861`); deliver the permission response. Actual helper replaces Save with **Approve** despite unsaved edits. The decision call sends only doctype, name and status (`request_approval.js:27–39`), then reloads the document. If clicked, it approves persisted values, not necessarily the edited values HR is viewing.

The reproduction uses the complete shipped JS helper in a VM, with controlled async response ordering. No real approval was submitted. The helper is shared by Leave Application, Shift Request, Expense Claim, OT Request, Attendance Request and Replacement Leave Claim.

**Correction:** bind responses to the requested document/revision, preserve Save while dirty, and refuse or explicitly save/reload before a decision. Recheck dirty state when the action is invoked, including Reject. Preserve use of the existing row-locked server decision API. Add delayed-response, document-navigation and edit-before-decision coverage.

This helper was introduced in `6c8751e56` on 4 September; it was not changed by the latest Hafiz range.

## Earlier Desk findings rechecked, not new

Local `fresh.local` metadata was queried in an explicit `START TRANSACTION READ ONLY` transaction, then rolled back and disconnected. No employees, salaries or identifiers were printed.

- **7 Sep D1:** all nine Nadi child Desktop Icons still have **zero role rows**. Source JSON agrees. This confirms the gating defect persists; workspace names being visible do not alone prove payroll data exposure.
- **7 Sep D2:** Professional Tax Deductions and Provident Fund Deductions still have **zero role rows** in the local DB, with their 2022 modified stamps. JSON has HR roles. Existing site/source parity remains broken.
- **7 Sep D3:** Shift & Attendance has **zero sidebar entries** for Shift Assignment Tool.
- **7 Sep D5:** standard Workspace Sidebar `HR` is still absent.
- Desk approval buttons do exist in the shared bundle helper. Do not reintroduce the older claim that Desk has no Approve/Reject implementation.

The local site is verification evidence, not proof of current production fixture state. The earlier statement that its scheduler is disabled has also become stale; the root audit checked current configuration separately.

## Verification and test-environment limits

New deterministic, read-only probes:

```sh
/home/nabil/verify-bench/env/bin/python docs/glass/audit/2026-09-08-desk-probes.py
node --test docs/glass/audit/2026-09-08-desk-probes.mjs
```

Python: **4 tests, 5 unmet assertions**, exit 1. JavaScript: **1 unmet assertion**, exit 1. These are intentional red audit properties. The Python command uses the bench interpreter because installed Frappe uses syntax not accepted by system Python 3.12. Functions are extracted unchanged from current source and executed with synthetic environment collaborators. They prove the stated seams, not complete HTTP/database/browser transactions.

Existing FILE-mode suites passed: workspace access (3), desktop fixtures (6), report-role integrity (2), report scope (2), scalar report filters (10), sync endpoints fenced (3), sync row isolation (3), stamp release (9), hub-owned parity (6), and sync runner (158 with `PYTHONPATH=.`): **202 tests**.

A combined pytest invocation failed 146 tests because test modules replace global `sys.modules['frappe']` with incompatible mocks; their own headers request file mode. The root's isolated pytest run also found a single sync runner failure: the test's frozen `NOW` is 10 August, while pytest's preinstalled Frappe mock supplies today's clock. `running_run` therefore correctly calls that record stale. `_load_module` only installs the test clock if Frappe is absent. File mode passes all 158; this is a test isolation defect, not evidence that force interrupts a genuinely running job. Repair clock ownership and mock cleanup; do not weaken the live-run guard.

Coverage included Desk launcher/metadata parity, report authorization entry points, report output/aggregate handling, shared approval helper, allocation grant/reversal ownership, sync overwrite/release guards, and relevant recent history. It did not execute production reports, publish notifications, modify permissions, perform a payroll calculation, run an authenticated Desk/browser flow, or replay a real allocation sync. No statement here certifies those paths as production-ready.

NEXT: include DS1–DS5 in the consolidated 360 audit; replay DS1/DS2 with synthetic authenticated report data, then design narrowly scoped permission and balance-ownership fixes before implementation. DEAD END: broad script-report-bypasses-all-permissions claim rejected after reading actual installed Frappe; combined pytest results are unsuitable without fixing global mock isolation.
