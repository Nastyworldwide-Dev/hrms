# AUDIT — request DATE MEANINGS vs DOWNSTREAM EFFECT, backend (21 Sep 2026)

Read-only. Repo `/home/nabil/nz-version-16` @ `a0b2e3a77` (nz-glass). Frappe v16 read at
`/home/nabil/verify-bench/apps/frappe`. Builds on
`docs/glass/audit/2026-09-21/A-approval-lifecycle.md` (Appendix A = state set / transitions;
not repeated). Every claim below is from JSON + controller + hooks; nothing was run.

Conventions. `Date` = fieldtype Date, JSON `'YYYY-MM-DD'`. `Datetime` = naive wall clock;
`creation`/`modified`/`approved_at` are on the **site** clock (`now_datetime()`, System
Settings tz, Asia/Dubai on the live site); `Employee Checkin.time` and `attendance_today()`
are on the **employee attendance** clock (`hrms/utils/timezone.py:120-140`, Malaysia/China
UTC+8). Frappe serialises every date/datetime with `str()`
(`frappe/utils/response.py:222-226`): Date → `'2026-09-21'`, Datetime →
`'2026-09-21 10:00:00.123456'` with **no timezone marker**.

Counts: **Critical 0 · High 3 · Medium 6 · Low 6.**

---

## §1 Per-type date table

`creation` (Datetime, site clock, immutable) exists on every row and is the only true
"filed at". `modified` (Datetime, site clock) is rewritten by every save, `db_set`,
`update_after_submit`, cancel, share and comment — it is never a business timestamp.

| Type | Business / effective date(s) | Fieldtype | Requested range | Approval / rejection timestamp | Cancel / withdrawal timestamp | Conflations |
|---|---|---|---|---|---|---|
| Leave Application | `from_date`, `to_date`, `half_day_date`; plus `posting_date` (default Today, permlevel 0, editable) | Date | from..to inclusive, holidays removed unless leave type `include_holiday` | **No field. No Version** (`track_changes` absent in JSON — also absent upstream). Proof = `Leave Ledger Entry.creation` where `transaction_name = name` (`leave_ledger_entry.py:66-83`), or `PWA Notification.creation`/`from_user` (`pwa_notifications.py:28-36`, only when employee has a user and decider ≠ employee). `modified`/`modified_by` only until the next touch. | docstatus 2: `modified`; `before_cancel` writes `status=Cancelled` (`leave_application.py:162`). **Ledger rows are hard-deleted on cancel** (`leave_ledger_entry.py:88-99`), so the approval proof above vanishes. Withdrawal of a draft = delete (`hrms/api/__init__.py:123-160`) → `Deleted Document.creation`. | `posting_date` = filing date AND the allocation-lookup date (`get_leave_allocation`, `:311-325`) AND the PWA list sort key (`get_leave_applications` `order_by="posting_date desc"`, `:1091`); the PWA seeds it from the **phone's** clock (`views/leave/Form.vue:30,72`) while the server default is site `nowdate()` (`:119`) — the two can disagree by a day. |
| Attendance Request | `from_date`, `to_date`, `half_day_date`; `in_time`, `out_time` | Date; Time | from..to inclusive, holidays skipped unless `include_holidays` | No field. `track_changes=1` → **Version** row with `changed: [["status","Open","Approved"],["docstatus",0,1]]` (`version.py:212-217`), `Version.owner` = decider. Also PWA Notification (on_submit only, `attendance_request.py:177`). Attendance rows it created: `Attendance.creation`. | docstatus 2: Version row `["docstatus",1,2]`; `modified`. Draft withdrawal → Deleted Document. | `in_time`/`out_time` are wall-clock Times combined with each requested day into naive Datetimes (`:118-126`) — same basis as `Attendance.in_time` (employee clock), fine. None. |
| Expense Claim | child `Expense Claim Detail.expense_date` (Date, default Today) = the real business date; parent `posting_date` (Date, default Today) = GL posting date; `clearance_date` | Date | none (list of dated lines) | No field. **No Version** (`track_changes` absent). Proof = `GL Entry.creation` (posting_date = claim posting_date; entries are reversed not deleted on cancel) or PWA Notification. `modified` moves again at **payment** (`set_status(update=True)` → `db_set` `expense_claim.py:108-111`) so `modified` ≠ approved-on for every paid claim. | docstatus 2: `modified`; `approval_status` stays `Approved` (no before_cancel), `status`→Cancelled. | `posting_date` is filing date, GL date, PWA sort key (`:1402`) **and the row date the PWA shows** (`ExpenseClaimItem.vue:73-75` always falls to `posting_date`; `from_date`/`to_date` never exist on this payload). `expense_date` is not returned by `get_expense_claims` at all (`:1378-1392`). PWA seeds `posting_date` from the phone clock (`views/expense_claim/Form.vue:57,88`). |
| Shift Request | `from_date`, `to_date` (optional = open-ended) | Date | from..to or from..∞ | No field. Version (`track_changes=1`). `Shift Assignment.creation` (`shift_request.py:48-68`). PWA Notification fires from **on_update** (`:34`) — so on a Desk Save without submit too (A-H4). | Version; `modified`. | none |
| OT Request | `ot_date` | Date | one day | No field. Version. `Leave Allocation`/ledger `creation` when RL (`ot_request.py:249-263`). PWA Notification (on_submit, `:241`). | Version; `modified`. | The RL allocation's `from_date`/ledger date is **`getdate()` = site today at approval**, not `ot_date` (`:257`) — approval date leaks into a business Date. |
| Replacement Leave Claim | `bank_month` (Date, read-only, = first day of the **creation** month) | Date | a month (informational only; the bank is deprecated `ot_request.py:281-295`) | No field. Version. Allocation/ledger `creation`. PWA Notification (`replacement_leave_claim.py:107`). | Version; `modified`. Reversal ledger dated `getdate()` (`hr/utils.py:836`). | `bank_month = get_first_day(getdate(self.creation))` (`:57-58`) — a Datetime on the site clock collapsed to a Date; `valid_from = getdate()` at approval (`:114`). |
| Compensatory Leave Request | `work_from_date`, `work_end_date`, `half_day_date` | Date | worked days | No field. Version. Allocation/ledger `creation`. PWA Notification (`compensatory_leave_request.py:105`). | Version; `modified`. | Allocation valid-from = `work_end_date + 1` (business date, correct). None. |
| Remote Checkin Request | `checkin_time` (Datetime, **employee clock**, copied from the punch) | Datetime | instant | **`approved_at`** (Datetime, site clock, `remote_checkin.py:373`, `remote_checkin_request.py:25-26`) + `approver` (Link) — the only type with a real decision stamp. Version too. | Not submittable; a decided row cannot be re-decided (`before_save` `:33-38`); delete → Deleted Document + Comment on the punch (`:58-79`). | `approved_at` also stamps a **Rejection** (name lies). `checkin_time` and `approved_at` are on two different clocks; "decided N minutes after the punch" would be 4 h off. `employee_checkin_after_insert.py:74` stamps `approved_at` for an *inherited* auto-approval. |
| Employee Advance | `posting_date` (default Today) | Date | none | Submitting IS approving: Version `["docstatus",0,1]`; `status` derives from payment. | Version; `modified`. | `posting_date` = filing + accounting date. |
| Travel Request | child `Travel Itinerary.departure_date`, `arrival_date` (**Datetime**), `check_in_date`, `check_out_date` (Date) | mixed | itinerary rows | Submitting IS approving: Version. | Version. | No parent date at all; `REQUEST_PERIOD_FIELDS` deliberately omits it (`approved_request_guard.py:66-72`). Itinerary Datetimes have no timezone semantics. |

Reading rule for "when was this approved / by whom":
* AR, Shift, OT, RL, Comp, Advance, Travel, Remote → `Version` (`ref_doctype`, `docname`, `data.changed` has `status`+`docstatus`, `owner`, `creation`); Remote also `approved_at`+`approver`.
* Leave Application, Expense Claim → **no Version**. Use the downstream row's `creation` (Leave Ledger Entry / GL Entry) or the PWA Notification row; after a Leave cancel, only the PWA Notification (if any) and the Email Queue remain.

---

## §2 Per-type downstream table

"Atomic" = inside the same `doc.submit()`/`doc.cancel()` save cycle that `decide()`/`finalize()`
run under a row lock (`approval.py:259,300,462,540-542`); any raise rolls back the decision.

| Type | On APPROVE writes | file:line | On CANCEL writes | file:line | Atomic? | Type-specific or generic | Can the domain write fail silently? |
|---|---|---|---|---|---|---|---|
| Leave Application | Leave Ledger Entry (1–2 rows, negative leaves; extra expiry row if allocation already expired), Attendance rows On Leave/Half Day (`insert`+`submit`, or `db_set` on an existing row), holiday-day Attendance deleted | `leave_application.py:135-160`, `327-393`, `804-831` | Ledger rows **deleted** (not reversed); Attendance rows set `docstatus=2` by raw `db.set_value` (no cancel chain) for ANY On Leave/Half Day row in range; day re-mark queued after commit | `:168-175`, `:395-409`, `leave_ledger_entry.py:88-99`, `hooks.py:519` → `day_remark_hooks.py:72-79` | Yes (ledger, attendance). Re-mark job: after commit, not atomic | Type-specific (`on_submit` guarded `status=="Approved"` inside `update_attendance`/`create_leave_ledger_entry`; Rejected writes nothing) | No — every write raises. But `cancel_attendance` cancels rows it did not create (any On Leave row in range) and never restores an Absent that the approval overwrote. |
| Attendance Request | Attendance rows Present/WFH/Half Day: new row `insert`+`submit`, or `db_set` status on an existing (same-shift or overlapping-shift) row + Info comment | `attendance_request.py:164-181`, `229-310` | Every Attendance with `attendance_request=name, docstatus 1` is **cancelled** — including pre-existing rows the approval only re-labelled; day re-mark after commit | `:215-227`, `hooks.py:562` | Yes | Type-specific | No raise-swallowing. Semantic hole: a row that was Present-by-punch and became WFH via the request is cancelled outright on cancel, not restored. |
| Expense Claim | GL Entries, task/project cost, reimbursed amount, Employee Advance claimed amount, exchange-gain JE | `expense_claim.py:247-255` | GL reversal, unlink Payment Entries, advance claimed amount | `:262-277` | Yes | Type-specific; second stage (Paid) via Payment Entry hooks `hooks.py:~455` | No |
| Shift Request | Shift Assignment `insert`+`submit` (start=from_date, end=to_date or open) | `shift_request.py:48-75` | Shift Assignment(s) with `shift_request=name` cancelled | `:77-88` | Yes | Type-specific | No |
| OT Request | If Approved **and** `compensation == Replacement Leave`: top-up or create `Leave Allocation` + ledger row valid from **site today**; stores `leave_allocation`, `leave_days_granted` via `db_set` | `ot_request.py:228-263`, `hr/utils.py:688-735` | `reverse_replacement_leave`: clamp to unused days, `db_set` new totals, negative ledger row dated **site today** | `:265-278`, `hr/utils.py:754-836` | Approve: yes. Cancel: yes, but **partial by design** | Type-specific; the Employee row lock in `decide()` is a per-type branch (`approval.py:252-265`) | **Yes on cancel**: allocation missing or cancelled → `frappe.log_error` + return, the request is cancelled anyway (`hr/utils.py:786-810`); days already taken are left allocated with only a msgprint + Comment (`:819-829`). Overtime-Pay OT writes nothing on approve; payroll prices it later. |
| Replacement Leave Claim | Top-up/create allocation valid from **site today**; `db_set leave_allocation` | `replacement_leave_claim.py:93-143` | `reverse_replacement_leave(claimed_days)` | `:145-154` | Same as OT | Type-specific (copy of OT's shape) | Same silent paths as OT cancel |
| Compensatory Leave Request | Top-up/create allocation valid from `work_end_date + 1`; throws if no Leave Period | `compensatory_leave_request.py:88-140` | Recompute days from dates (not stored), `validate()` the allocation, `db_set`, negative ledger dated `work_end_date+1` | `:142-164` | Yes | Type-specific | No silent path — but **no clamp and it calls `validate()`**, the exact freeze `reverse_replacement_leave` documents (`hr/utils.py:764-772`; memory "Leave Allocation validate gotcha"). Withdrawal after the comp day was taken cannot complete. |
| Remote Checkin Request | `Employee Checkin` flags via `db.set_value` (`requires_remote_approval=0`, `remote_approval_status`); late-checkout day rebuilt inline; day re-mark enqueued after commit; push to employee | `remote_checkin_request_hooks.py:451-503` | n/a (not submittable) | — | Checkin flags: yes (same `save()`). Re-mark: after commit, `except Exception: logger.exception` (`:517-521`) | Type-specific hook | Yes — the re-mark and the skip-reason Comment swallow exceptions by design (`:520`, `:548-549`). |
| Employee Advance | GL/status via ERPNext accounting; nothing in `on_submit` here | `employee_advance.py:30-60` | `set_status`, linked PE check | `:62-65` | Yes | Generic (submit is the decision) | No |
| Travel Request | nothing | `travel_request.py:10-12` | nothing (guard only, `hooks.py:554`) | — | — | — | — |

Generic layer: `decide()`/`finalize()` (`approval.py:230-310, 413-552`) do the lock, access,
idempotency, revision check and one `submit()`/`cancel()`. They know nothing about dates or
downstream rows — good. The per-type knowledge lives in seven `on_submit`/`on_cancel`
methods with the same skeleton copied seven times (see §5).

---

## §3 State × timestamp proof table

State set per Appendix A. Per transition: which record proves WHEN and WHO.

| Transition | Types | WHEN | WHO | Gaps |
|---|---|---|---|---|
| filed (→ pending/0) | all | `creation` (site clock) | `owner` | PWA `posting_date` may be the phone's date (Leave, Expense). |
| decided (pending/0 → Approved∣Rejected/1) via `decide` | AR, Shift, OT, RL, Comp | `Version.creation` (status + docstatus in one diff) | `Version.owner` = `frappe.session.user` (routed approvers included, since `ignore_permissions` does not skip Version) | none |
| decided via `decide` | **Leave, Expense** | nothing on the row. `Leave Ledger Entry.creation` / `GL Entry.creation`; `PWA Notification.creation` (only if employee has `user_id` and decider ≠ employee, `pwa_notifications.py:22-26`); `modified` until the next write | `PWA Notification.from_user`; `modified_by` until the next write; ledger/GL `owner` | **Rejected Leave/Expense leaves no downstream row** → only the PWA Notification (may not exist) proves who rejected and when. Paid Expense: `modified` = payment time. |
| decided-but-draft (pending/0 → Approved/0, Desk Save) | Leave, Expense, Shift | Shift: Version. Leave/Expense: PWA Notification only (fires from `on_update`, A-H4) | as above | The later `finalize(submit)` creates **no second notification** (`has_value_changed` false), so the notification's time is the draft-decision time, not the transaction time. |
| cancelled (X/1 → 2) | all submittable | Version (`["docstatus",1,2]`) for the tracked five; Leave/Expense: `modified` only | `modified_by`; Version.owner | Leave: `status=Cancelled` overwrites the decision value and the ledger rows are deleted → after cancel nothing on the row or in the ledger says it was ever Approved, by whom, or when. |
| withdrawn draft (delete) | Leave, Expense, Shift, AR, OT, RL | `Deleted Document.creation` | `Deleted Document.owner` | fine |
| Remote decided | Remote Checkin | `approved_at` (site clock) + Version | `approver` field = assigned approver, **not necessarily the decider** (HR may decide; `may_decide` `remote_checkin_request.py:126`) → decider only in `Version.owner`/`modified_by` | `approved_at` is set on Reject too. |
| paid (Approved/1, status Unpaid → Paid) | Expense | `modified` (via `db_set`) / Payment Entry `posting_date` | Payment Entry owner | `modified` no longer reflects approval. |

---

## §4 Date-only safety on the backend — findings with file:line

Serialisation is safe: every list endpoint in `hrms/api/__init__.py` returns Date columns as
`'YYYY-MM-DD'` strings via `frappe.get_list` + `json_handler` (`get_shift_requests:431-455`,
`get_attendance_requests:476-503`, `get_ot_requests:533-552`, `get_replacement_leave_claims:576-592`,
`get_leave_applications:1065-1099`, `get_expense_claims:1378-1412`). `get_attendance_calendar_events`
(`:362-385`) keys its dict with `date.strftime('%Y-%m-%d')` and compares `datetime.date`
objects from `get_all` with `getdate(from_date)` — type-consistent. Holidays are `pluck`ed as
`date` objects and compared the same way (`:404-412`). No endpoint returns a `now_datetime()`
where a Date is meant.

What is NOT safe is which clock "today" is read from, and where a Datetime is collapsed to a
Date:

| # | Location | What | Effect |
|---|---|---|---|
| D1 | `ot_request.py:257` `grant_replacement_leave(..., getdate(), ...)`; `replacement_leave_claim.py:114` `valid_from = getdate()`; `hr/utils.py:836` reverse ledger `getdate()` | approval-time **site** date written into `Leave Allocation.from_date` / ledger `from_date` | A business Date carries the approver's tap date, on the wrong clock. Approve at 02:30 MYT on the 1st → allocation dated the previous day, previous month, possibly previous Leave Period (`get_leave_period(valid_from, …)` picks the period by this date, `hr/utils.py:698-703`). |
| D2 | `replacement_leave_claim.py:57` `getdate(self.creation)` → `bank_month` | Datetime (site clock) collapsed to a Date | claim filed 01:00 MYT on the 1st → `bank_month` = previous month. Informational since the bank is deprecated, but it is the value the PWA shows as "Bank Month" (`REPLACEMENT_LEAVE_CLAIM_FIELDS`, `requestSummaryFields.js:318-321`). |
| D3 | `ot_request.py:114` `today = getdate()` (site) vs `ot_date` (employee's day); `get_claimable_ot_summary` uses `employee_now(employee).date()` (`hrms/api/__init__.py:656`) | filing-window and "OT Date cannot be in the future" measured on the site clock while the claimable summary is on the employee clock | Between 00:00 and 04:00 MYT the two disagree: the summary lists a day the validator refuses as "future", and `earliest_filable_date` shifts by one day at the boundary (`filing_window.py:56-68`). |
| D4 | `leave_application.py:210` backdated check `getdate(self.from_date) < getdate()` (site); `:154` expiry-row test `to_date < getdate()`; `:312` `posting_date or getdate()` | site "today" for an employee-local business rule | 4 h window daily where "backdated" is judged on the wrong day. Low impact (roles decide, not refuse). |
| D5 | PWA seeds `posting_date` from the phone clock: `views/leave/Form.vue:30,72`, `views/expense_claim/Form.vue:57,88`; server fallback is site `nowdate()`/`today()` (`leave_application.py:119`, `expense_claim.py:125`) | two clocks for one Date | `posting_date` ≠ `date(creation)` for filings in the 00:00–04:00 MYT window; Leave allocation lookup (`:311-325`) and the PWA list order (`:1091`, `:1402`) key on the phone's date. |
| D6 | `frontend/src/views/Notifications.vue:97` `dayjs(item.creation).fromNow()`; `RequestPanel.vue:139-141` `new Date(b.creation)`; `helpdesk.js:56-77`, `IssueList.vue:85`, `HRIssueBoard.vue:66,113` | site-clock naive Datetime parsed as **device-local** | "Your Leave has been Approved … 4 hours ago" the second it lands, on every Malaysian phone. This is the one place the employee is shown *when* a decision happened, and it is wrong by the site–device offset. |
| D7 | `Remote Checkin Request.checkin_time` (employee clock) vs `approved_at` (site clock) on one row; `remote_checkin.py:338` orders decided rows by `approved_at` | two clocks, one row | Any "punch → decision" latency or same-day grouping would be 4 h off. Sorting alone is unaffected. |
| D8 | `attendance_request.py:118-126` `datetime.combine(getdate(date), get_time(self.in_time))` | Time × Date → naive Datetime | Correct basis (matches `Attendance.in_time`, employee wall clock). No defect; listed because it is the one Date×Time combine in the request path. |
| D9 | `approval.py:317` `get_datetime(doc.modified) != get_datetime(expected_modified)` | Datetime string round-trip | Safe: the client echoes the server's own string; microseconds survive `str()`. |
| D10 | Leave `cancel_attendance` `:395-409` `attendance_date.between(self.from_date, self.to_date)` | Date vs Date | Safe types; scope defect noted in §2. |

No comparison of a Date field with a Datetime was found in the request path. The generic
"today" helpers (`getdate()`, `nowdate()`, `today()`) all resolve on the site clock; only
`hrms/utils/timezone.py` and `get_claimable_ot_summary` use the employee clock.

---

## §5 Over-generic vs could-be-data

**Too broad (treats all types alike where the meaning differs)**

| Where | What it flattens |
|---|---|
| `PWANotificationsMixin.notify_approval_status` (`pwa_notifications.py:14-36`) | Same message for a decision that pays out (OT-RL, Comp, RL, AR) and one that does not; called from `on_update` for Leave/Expense/Shift (fires on a draft save) and from `on_submit` for the other four — the *same* method means two different events. Message carries no date at all. |
| `approved_request_guard.REQUEST_PERIOD_FIELDS` (`:55-73`) | Good table — but `Expense Claim: ("posting_date",)` reads the GL/filing date as "the period paid", while the paid period is the child rows' `expense_date`; `Replacement Leave Claim: ("bank_month",)` reads a creation-derived month. The payroll-overlap check therefore compares the wrong Date for two of nine types. |
| `finalize()` else-branch (`approval.py:474-521`) | Cancel of every type goes through one branch that does not know some cancels are **partial** (OT/RL clamp) or can **freeze** (Comp `validate()`); it returns `_state(doc)` = status+docstatus only, so the PWA cannot tell "cancelled, 0.5 day stays allocated" from a clean reversal. |
| `requestSummaryFields.js` (`frontend/src/data/config/requestSummaryFields.js`) | Static per-type field lists; **no `Compensatory Leave Request` entry** (`REQUEST_SUMMARY_FIELDS:352-359`) although it is in `DECIDE_THEN_SUBMIT`; no entry shows `creation` ("filed on") or any decision time; Expense shows `posting_date` labelled "Posting Date" and not the expense dates. |
| `get_filters()` (`hrms/api/__init__.py:942-976`) | `"Open" if doctype == "Leave Application" else "Draft"` + a hard-coded 3-tuple exclusion re-derive what `DECIDE_THEN_SUBMIT[dt][1]` already says. |
| `ExpenseClaimItem.vue:73-83` | Renders `posting_date` as the claim's date because the generic item contract expects `from_date`/`to_date`. |

**Per-type branches that could be one table (a `RequestPolicy` row per doctype)**

| Branch | Lines | Column it would become |
|---|---|---|
| `decide()` OT-only Employee pre-lock | `approval.py:252-265` | `lock_parent: "employee"` |
| `_get_doc_approver` if-chain | `pwa_notifications.py:91-109` | `approver_resolver` |
| `APPROVAL_STATUS_FIELD`, `APPROVER_FIELD`, `EMPLOYEE_APPROVER_FIELD`, `SELF_APPROVAL_SETTING`, `DECISION_FIELD_BY_DOCTYPE`, `APPROVER_FIELD_MAP`, `WITHDRAWABLE_REQUEST_DOCTYPES`, `REQUEST_PERIOD_FIELDS` | A-L5 lists the first six; add `WITHDRAWABLE_REQUEST_DOCTYPES` (`__init__.py:111-120`, omits Comp Leave) and `REQUEST_PERIOD_FIELDS` | `decision_field`, `pending_value`, `approver_field`, `period_fields`, `withdrawable` |
| Seven `on_submit` bodies: self-fence → attachment → "must be Approved or Rejected" → notify → `if Approved: grant()` | `attendance_request.py:164-181`, `shift_request.py:48-75`, `ot_request.py:228-263`, `replacement_leave_claim.py:93-108`, `compensatory_leave_request.py:88-106`, `leave_application.py:135-160`, `expense_claim.py:239-255` | one mixin `on_submit` + per-type `grant()`/`reverse()`; the notify placement inconsistency (on_update vs on_submit) disappears with it |
| Three copies of "top-up or create Leave Allocation + ledger" | `hr/utils.py:688-735`, `replacement_leave_claim.py:110-143,171-189`, `compensatory_leave_request.py:108-140,182-200` | one helper taking `(leave_type, valid_from, days)`; Comp's reverse would then inherit the clamp |
| `order_by` per list endpoint (`creation desc` ×4, `posting_date desc` ×2) | `__init__.py:451,500,549,589,1091,1402` | `list_sort` column; today Leave/Expense rows sort by a phone-supplied Date |

---

# Findings

## High

### H1. Leave Application and Expense Claim keep no record of when or by whom they were decided; cancelling a Leave erases the only proof
**Problem.** Neither doctype has `track_changes`, so no `Version` is written on decide/cancel. The only DB evidence of an approval is the Leave Ledger Entry / GL Entry `creation` and the PWA Notification row. A Leave cancel hard-deletes the ledger rows (`leave_ledger_entry.py:88-99`) and overwrites `status` with `Cancelled` (`leave_application.py:162`). A **rejection** of either type writes no downstream row at all.
**Location.** `hrms/hr/doctype/leave_application/leave_application.json` (no `track_changes`); `expense_claim.json` (same); `leave_application.py:162-175`; `pwa_notifications.py:22-26` (notification skipped when employee has no user or decider = employee).
**Root cause.** Upstream never tracked these two; the fork added tracking to its own five doctypes but not to the two it inherited, and relies on `modified`/`modified_by`, which payment (`expense_claim.py:108-111`), cancel and allow-on-submit edits (`follow_via_email`, `project`, `cost_center`) overwrite.
**User impact.** HR asked "who approved this leave and when" for a cancelled or disputed leave has nothing on the row and nothing in the ledger; for a rejected Expense there is only the notification (if any). An audit of approver behaviour (A-M7 "manager decided a request named to someone else") cannot be reconstructed.
**Recommended change.** Add `"track_changes": 1` to both JSONs (guarded patch, per memory "Property Setter shadows doctype JSON"); this yields the same `Version` proof the other five have with zero code. Separately: stop deleting Leave Ledger Entry rows on cancel (write a reversing +row, as Comp/RL do) — a policy change for Nabil to rule on, since balances and reports read the ledger.
**Now / separately.** `track_changes` now (JSON + patch, no behaviour change). Ledger reversal separately (policy).

### H2. Replacement-Leave grants are dated by the approver's tap on the site clock, not by the worked day
**Problem.** `OTRequest.on_submit` passes `getdate()` as `valid_from` (`ot_request.py:257`); `ReplacementLeaveClaim.add_to_leave_allocation` does the same (`replacement_leave_claim.py:114`); the reversal ledger row uses `getdate()` too (`hr/utils.py:836`). `getdate()` is site "today" (Dubai). The allocation `from_date`, the Leave Period chosen, and `_existing_rl_allocation`'s match all key on that date.
**Location.** As above; `hr/utils.py:698-703` (period lookup on `valid_from`).
**Root cause.** "Valid from approval" was implemented as "valid from now", and "now" was left on the audit clock the timezone module tells callers not to use for business dates (`timezone.py:5-8` says the opposite direction — approvals stay on the system clock — which is right for `approved_at` and wrong for a Date that decides which allocation gets the days).
**User impact.** Two OT approvals for the same employee made either side of a Leave Period boundary (or a month boundary near 00:00–04:00 MYT) land in different allocations; a cancel then reverses against the allocation that happens to cover *today*, not the one the grant went into (`reverse_replacement_leave` reads `leave_allocation` by name, so the reversal itself is right, but the reversal ledger row is dated today, so a period balance report shows the −0.5 in a different period than the +0.5). Comp Leave does this correctly (`work_end_date + 1`).
**Recommended change.** `valid_from = getdate(self.ot_date)` for OT; for RL claim keep "today" but on `attendance_today(self.employee)`; reversal ledger row dated the allocation's `from_date` (or the original grant date, which is what Comp does). One table-driven test: for each granting type, the ledger `from_date` equals the business date, not `nowdate()`.
**Now / separately.** Now for OT (one line + test; touches balances only for future approvals). RL-claim and reversal date separately (RL claim is deprecated).

### H3. The one place the employee is shown *when* a decision happened is off by the site–device timezone gap
**Problem.** PWA Notification `creation` is a naive site-clock Datetime (`'2026-09-21 10:00:00.123'`). `Notifications.vue:97` does `dayjs(item.creation).fromNow()`, which parses it as device-local time. On a Malaysian phone against a Dubai site, an approval that just landed reads "4 hours ago"; the same skew hits `RequestPanel.vue:139-141` ordering (harmless), helpdesk and issue lists (`helpdesk.js:56-77`, `IssueList.vue:85`, `HRIssueBoard.vue:66,113`).
**Location.** `frontend/src/views/Notifications.vue:97`; `frontend/src/data/notifications.js:23,29`; no timezone handling anywhere in `frontend/src` (grep `utcOffset|timezone` → none).
**Root cause.** Site-clock Datetimes are serialised without an offset, and the client has no notion of the site timezone (`frappe.boot.time_zone` is not read by the PWA).
**User impact.** Employees see approvals/rejections time-shifted; HR reading the Issue board sees the same shift. Combined with A-C1 (stale Home panel) the employee's picture of *when* things happened is wrong twice over.
**Recommended change.** Return the site timezone once (`get_current_user_info` already exists, `__init__.py:59`) and parse every `creation`/`modified` with `dayjs.tz(value, siteTz)` (dayjs `timezone` + `utc` plugins, both already installable without a new dep — check `package.json`); or have the server emit ISO-8601 with offset for the notification list. One grep-style test: no `dayjs(x.creation)` without the tz helper.
**Now / separately.** Now (small, self-contained) — it is the visible symptom of the whole date question.

## Medium

### M1. Expense Claim's real dates never reach the PWA; `posting_date` stands in for them everywhere
**Problem.** `get_expense_claims` (`__init__.py:1378-1392`) returns `posting_date` twice and no `expense_date`; `ExpenseClaimItem.vue:73-75` renders `posting_date` as the row date; `REQUEST_PERIOD_FIELDS` uses `posting_date` as "the period paid" (`approved_request_guard.py:57`); the PWA seeds `posting_date` from the phone (`Form.vue:57,88`).
**Location.** As above. **Root cause.** One field carrying filing date + GL date + display date. **User impact.** A claim for last month's receipts filed today shows today; the payroll-overlap guard tests today's payslip, not the receipts' month, so an employee can withdraw a claim whose expenses were already reimbursed in an earlier period (the exact failure the Travel Request comment describes, `approved_request_guard.py:66-72`). **Recommended.** Return `MIN(expense_date)`/`MAX(expense_date)` from the child table in `get_expense_claims` (the query already joins it for the COUNT); render those in the item; make the guard read the child min/max (`REQUEST_PERIOD_FIELDS` would need a child-aware entry). **Now / separately.** List + item now; guard separately (money rule).

### M2. Cancel of an approved OT / RL claim can silently leave the balance untouched
**Problem.** `reverse_replacement_leave` logs (`frappe.log_error`) and returns when the allocation is missing or not submitted (`hr/utils.py:786-810`), and clamps to unused days with only a `msgprint` + allocation Comment (`:819-829`). The cancel succeeds; `finalize()` returns `{docstatus: 2}`; the PWA toasts success.
**Location.** As above; `approval.py:541-552`. **Root cause.** Deliberate "the cancel must still work" ruling — correct — with no channel back to the actor. **User impact.** An approver withdraws an approval believing the days came back; the employee keeps them; HR finds out from an Error Log nobody reads. **Recommended.** Return the reversal outcome from `on_cancel` via `doc.flags` (the Remote Checkin `late_checkout_repair` pattern, `remote_checkin.py:381-389`) and include it in `_state()`; the sheet toasts "Cancelled — 0.5 day stays allocated (already taken)". **Now / separately.** Separately (touches `_state` contract).

### M3. Compensatory Leave cancel has no clamp and calls `validate()` — the freeze RL already fixed
**Problem.** `compensatory_leave_request.py:142-164` recomputes days from dates, subtracts without checking taken days, then `leave_allocation.validate()` — which throws "Total leaves allocated is mandatory" when the sole grant reverses to zero (memory: "Leave Allocation validate gotcha"; `hr/utils.py:764-772` documents it). **User impact.** HR/approver cannot withdraw a comp-leave approval once the employee has used the day, or when it was the employee's only comp grant: the cancel throws, the request stays Approved. **Recommended.** Route through `reverse_replacement_leave`-style shared reverse (parametrised by leave type) — the third copy §5 lists. **Now / separately.** Now (one call swap + test "cancel after the day was taken completes and leaves 0 day reversible").

### M4. Attendance Request cancel destroys rows it only re-labelled; Leave cancel cancels rows it did not create
**Problem.** AR approval `db_set`s `status` + `attendance_request=name` on a pre-existing Attendance (`attendance_request.py:236-262`); AR cancel then cancels every Attendance with `attendance_request=name` (`:215-227`), so a punch-marked Present that the request turned into WFH is **cancelled**, not restored to Present. Leave cancel sets `docstatus=2` via raw `db.set_value` on every On Leave/Half Day row in the date range (`leave_application.py:395-409`), regardless of `leave_application` link, and bypasses Attendance's cancel chain (no Version, no day re-mark of its own — the `remark_request_days` hook covers it).
**Root cause.** Approval's downstream write is not journaled (old status not kept), so cancel cannot invert it. **User impact.** Withdrawing an AR removes a day the employee genuinely worked from the calendar and payroll until the hourly job re-marks it (the re-mark hook exists for Leave/AR cancel, `hooks.py:519,562`, so the gap closes within the hour — but a manual Attendance edited by HR is gone for good). **Recommended.** Store the pre-approval status on the Attendance row (a Comment already is; a field is better) and restore instead of cancel when the row predates the request. **Now / separately.** Separately (Attendance write path is under the "two rebuild paths, one guard" memory).

### M5. Decision notifications fire at different lifecycle points per type and carry no time
**Problem.** Leave/Expense/Shift call `notify_approval_status()` from `on_update` (`leave_application.py:134`, `expense_claim.py:230`, `shift_request.py:34`); AR/OT/RL/Comp from `on_submit`. For the first three a Desk Save without submit (A-H4) creates the row, and the later submit creates none, so `PWA Notification.creation` — the H1 fallback proof — records the draft edit, not the transaction. The message (`pwa_notifications.py:32`) names no date.
**Recommended.** Move the three calls into `on_submit` (A-H4's fix (1)) and include `frappe.format(now_datetime(), {"fieldtype":"Datetime"})` — or better, nothing, and let H3 render `creation` correctly. **Now / separately.** With A-H4.

### M6. `REQUEST_PERIOD_FIELDS` compares payroll against filing/creation-derived dates for two types
Covered under M1 (Expense `posting_date`) and D2 (RL `bank_month` from `creation`). One table row each; listed so the money-rule fix is tracked as its own slice.

## Low

### L1. `approved_at` is written on rejection too, and `approver` is the routed approver, not the decider
`remote_checkin.py:373`, `remote_checkin_request.py:25-26`, `may_decide:126`. Rename is a schema change; at minimum document that `Version.owner`/`modified_by` is the decider. Separately.

### L2. `bank_month` derives from `creation` on the site clock
`replacement_leave_claim.py:57-58` (D2). Deprecated flow; leave.

### L3. OT filing window judged on the site clock while the claimable summary is on the employee clock
`ot_request.py:114` vs `__init__.py:656` (D3). Replace `getdate()` with `attendance_today(self.employee)` in `validate_filing_window`. Now if touching OT anyway (one line); otherwise separately.

### L4. Leave backdating / expiry checks use site "today"
`leave_application.py:154,210,312` (D4). Same one-line swap; low impact.

### L5. `REQUEST_SUMMARY_FIELDS` lacks Compensatory Leave Request; `WITHDRAWABLE_REQUEST_DOCTYPES` lacks it too
`requestSummaryFields.js:352-359`; `__init__.py:111-120`. The sheet renders no summary for a Comp request and an employee cannot withdraw their own Comp draft. Add both entries (data only). Now.

### L6. `posting_date` returned twice, and the list sorts by a phone-supplied Date
`__init__.py:1067,1080,1091` and `:1380,1388,1402`. Drop the duplicate; sort by `creation desc` like the other four endpoints. Now (trivial).

---

## Answers to the five questions, in one line each

1. **Dates**: `creation` is the only reliable "filed"; business dates are all `Date` except Remote Checkin (`Datetime`, employee clock) and Travel itinerary; only Remote Checkin has a decision timestamp field; Leave/Expense have no Version; `posting_date` is triple-booked on Leave/Expense.
2. **Downstream**: every type's write is inside the same `submit()`/`cancel()` as the decision (atomic), type-specific, guarded on `status == "Approved"`; the silent-failure paths are all on **cancel** (OT/RL reversal skip/clamp; Remote re-mark) plus a freeze on Comp cancel.
3. **Proof**: Version for five types + Advance/Travel/Remote; ledger/GL/notification `creation` for Leave/Expense; nothing survives a Leave cancel except the notification.
4. **Date-only**: serialisation is correct everywhere; the defects are clock choice (site vs employee vs phone) at D1–D6, with H2 (allocation dates) and H3 (notification times) the ones users see.
5. **Generic vs data**: eight parallel per-type maps and seven copied `on_submit` skeletons want one policy table; `REQUEST_PERIOD_FIELDS` is the right shape but wrong for two rows; `finalize()`'s single cancel branch hides partial reversals.
