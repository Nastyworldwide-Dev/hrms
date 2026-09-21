# AUDIT — request approval lifecycle, backend + NADI PWA (21 Sep 2026)

Read-only. Nothing edited, nothing run that writes. Repo `/home/nabil/nz-version-16`,
branch `nz-glass` at `ff7ef690b`. Frappe source cross-read from
`/home/nabil/verify-bench/apps/frappe` (realtime, documentResource semantics).

Scope: Leave Application, Expense Claim, Shift Request, OT Request, Attendance Request,
Replacement Leave Claim, Compensatory Leave Request (all seven `DECIDE_THEN_SUBMIT`
members), Employee Advance / Travel Request (guard-only, `field=None`), and Remote
Checkin Request (its own non-submittable path).

Already known — cited, not re-discovered:
* `.claude/plans/ticket-approval-refactor.md` — `_decision_access` is four policies in
  one function; DecisionPolicy refactor deferred.
* `.claude/plans/ticket-unfenced-self-submission.md` — Employee Advance and Travel
  Request have no self-approval fence at all (Desk-only exposure).
* `.claude/plans/audit-2026-09-13-approver.md` — sight vs action disagree (reports_to
  manager can decide Leave/Expense/Shift named to someone else; System Manager is in
  `_is_routed_approver` and only fails closed by ordering; OT row scope has no company
  fence; seven derivations of "my team").

Counts: **Critical 1 · High 4 · Medium 8 · Low 9.**

---

## Best explanation for "approver says approved, employee still sees Open"

The employee's Home → My Requests panel (and the Leave dashboard's recent list) is fed by
module-scope resources (`myLeaves`, `myOTRequests`, …) that are fetched **once per page
load** and afterwards refreshed by **exactly one channel**: a socket.io event
`hrms:refetch_resource` addressed to the employee's user room. Nothing else ever reloads
them — not navigation, not app resume, not pull-to-refresh (Home has none), not a
notification tap. socket.io events are fire-and-forget; an approval that lands while the
employee's phone is asleep, offline, or after its socket gave up (`reconnectionAttempts:
5`) is simply lost, and the panel keeps saying "Open" until the app is fully reloaded.
The DB is correct (`decide()` is atomic); the display is stale. The Leave History list
and the detail page fetch on mount and therefore show "Approved" — which is why the
report reads as "PWA still shows Open" rather than "nothing shows Approved".

Evidence chain: `frontend/src/data/leaves.js:20-39` (auto, cached, no other reload) →
`frontend/src/components/RequestPanel.vue:146-160` (list_update reloads team/history
only, never `my*`) → `frontend/src/socket.js:16,19-27` (5 reconnect attempts; the only
`my*` reload path) → `frontend/src/composables/realtime.js:43-52` (reconnect rejoins
rooms, reloads nothing) → `frontend/src/utils/personalCache.js:84-90` (focus /
visibilitychange only check the session, never refetch) → `hrms/hr/doctype/leave_application/leave_application.py:180-183`
(server publishes once, after commit, to `user:<Employee.user_id>`).

For OT Request and Replacement Leave Claim the situation is worse: the server never
publishes a `my_*` refetch at all (H2), so their rows are stale from the first tap.

---

# Critical

## C1. The employee's "My Requests" is never refreshed except by a one-shot socket event

**Problem.** `myLeaves`, `myClaims`, `myShiftRequests`, `myAttendanceRequests`,
`myOTRequests`, `myReplacementLeaveClaims` are `createResource({auto: true, cache})` at
module scope. They fetch once when the bundle evaluates. The only later reload is
`socket.on("hrms:refetch_resource")` → `resource.reload()`. No view, layout, router
guard, visibility handler or pull-to-refresh calls `.reload()` on any of them.

**Location.**
* `frontend/src/data/leaves.js:20-39` — `myLeaves` (`auto: true`, `cache: personalCacheKey("hrms:my_leaves")`).
* `frontend/src/data/overtime.js:36-58`, `frontend/src/data/attendance.js:49-90`, `frontend/src/data/claims.js:19-38` — same shape.
* `frontend/src/socket.js:19-27` — the one reload path.
* `frontend/src/components/RequestPanel.vue:146-160` — `list_update` handlers reload `team*` and `history*` only.
* `frontend/src/views/Home.vue` — no `GPullRefresh`, no reload on enter.
* `frontend/src/views/leave/Dashboard.vue:60-61,92` — renders `myLeaves.data`, no reload.
* `frontend/src/utils/personalCache.js:84-90` — `focus`/`visibilitychange` call `sessionIsCurrent()` only.
* `frontend/src/composables/realtime.js:43-52` — on `connect` rejoins doctype rooms; does not reload anything.

**Root cause.** Realtime was treated as a delivery guarantee. It is not: Frappe's
`publish_realtime(..., after_commit=True)` emits once (`frappe/realtime.py:73-83`); a
socket that is disconnected, asleep, or in another room at that instant never receives
it, and there is no replay. Every other read surface (ListView, FormView) fetches on
mount, so the defect is confined to the Home panel and the three dashboards that reuse
the `my*` resources.

**User impact.** Employee opens the app that has been sitting in the background since
morning; Home says the leave is "Open"; the approver says it is approved. Also: a leave
the employee just filed does not appear on Home if the socket is down; a withdrawn
request stays listed. Employees escalate to HR; HR opens Desk and sees the truth.

**Evidence.**
```
leaves.js:31-32     auto: true,
                    cache: personalCacheKey("hrms:my_leaves"),
socket.js:19-27     socket.on("hrms:refetch_resource", (data) => { … resource.reload() })
RequestPanel.vue:146-149
                    useListUpdate(socket, "Leave Application", () => {
                        teamLeaves.reload()
                        historyLeaves.reload()
                    })
realtime.js:46-51   socket.on("connect", () => { … socket.emit("doctype_subscribe", doctype) })
```
`grep -rn "myLeaves.reload\|myOTRequests.reload" frontend/src` → no hits outside data/.

**Recommended change (smallest that holds).**
1. `RequestPanel.vue` `onMounted`: also reload the six `my*` resources (they are cheap,
   limit 10) and register `useListUpdate` callbacks that reload `my*` too.
2. `realtime.js` `wireReconnect`: after rejoining rooms, call a registered
   "on reconnect" hook that reloads the `my*`/`team*` resources (a missed event is the
   normal case on mobile, not the exception).
3. Add `GPullRefresh` to Home (ListView already has the component).
4. Optional: reload on `visibilitychange → visible` when the page was hidden for more
   than N seconds.
Invariant test: "every resource keyed `hrms:my_*` is reloaded by at least one non-socket
path" (grep-style test like `request-status-chip.test.mjs`).

**Fix now or separately.** Now — it is the reported symptom.

---

# High

## H1. socket.io gives up after 5 reconnect attempts; realtime dies for the page's lifetime

**Problem.** `io(url, { reconnectionAttempts: 5 })`. socket.io-client 4.6.1 stops
reconnecting after 5 failures (`node_modules/socket.io-client/build/esm/manager.js:316-319`,
emits `reconnect_failed`, `_reconnecting=false`, never retries). Nobody in the app
listens for `reconnect_failed` or calls `socket.connect()` again. Default backoff
(1s → 5s cap) exhausts five attempts in roughly 10–25 s of no connectivity.

**Location.** `frontend/src/socket.js:14-17`. History: inherited from upstream
("fix: add reconnection attempts for socket").

**Root cause.** A desktop-era guard against reconnect storms applied to a standalone
mobile PWA that lives for days and routinely loses the network for longer than 20 s.

**User impact.** After one bad-signal lift ride every realtime feature is dead until a
full reload: `my*` panels (C1), approver Team tab, notifications badge, remote check-in
approvals banner, the attendance calendar refresh. Invisible: nothing on screen says the
socket is gone.

**Evidence.**
```
socket.js:14-17    let socket = io(url, { withCredentials: true, reconnectionAttempts: 5 })
manager.js:316     if (this.backoff.attempts >= this._reconnectionAttempts) { … emitReserved("reconnect_failed") …
```

**Recommended change.** Drop `reconnectionAttempts` (default Infinity) or set it high
with `reconnectionDelayMax` ~30 s; on `reconnect_failed` or `visibilitychange→visible`
with `!socket.connected`, call `socket.connect()`. Pair with C1's reload-on-reconnect.

**Fix now or separately.** Now, with C1 (one commit, one cause: "realtime is not a
guarantee").

## H2. OT Request, Replacement Leave Claim, Compensatory Leave Request never publish a `my_*` refetch

**Problem.** Leave, Expense, Shift and Attendance controllers call
`hrms.refetch_resource("hrms:my_<x>", employee_user)` from `on_update`/`on_cancel`.
OT Request, Replacement Leave Claim and Comp Leave do not call `refetch_resource` at
all. The PWA's `myOTRequests` / `myReplacementLeaveClaims` therefore have **no** refresh
path whatsoever after page load.

**Location.**
* `hrms/hr/doctype/ot_request/ot_request.py` — `grep refetch_resource` → 0 hits.
* `hrms/hr/doctype/replacement_leave_claim/replacement_leave_claim.py` — 0 hits.
* `hrms/hr/doctype/compensatory_leave_request/compensatory_leave_request.py` — 0 hits.
* Contrast `hrms/hr/doctype/leave_application/leave_application.py:180-183`,
  `attendance_request.py:464-467`, `shift_request.py:40-43`, `expense_claim.py:242-245`.
* Frontend keys expected: `frontend/src/data/overtime.js:40,56`.

**Root cause.** The three doctypes were added to the decision flow on 26 Aug / 15 Sep
without the `publish_update` twin that the upstream four carry.

**User impact.** An approved/rejected OT claim or replacement-leave claim shows
"Pending" on Home until a full app reload, every time. For the approver, the Team tab
row is dropped only via `list_update` (works while the socket is alive).

**Evidence.** `grep -rn "refetch_resource" hrms --include=*.py` lists only
employee_advance, attendance_request, pwa_notification, expense_claim, attendance,
leave_application, shift_request, employee_master.

**Recommended change.** Add `publish_update()` (my + team keys) to the three
controllers' `on_update` and `on_cancel`, mirroring `shift_request.py:32-43`; add the
three to the `test_notification_delivery_after_commit`-style pin. Still subordinate to
C1 — without a non-socket reload this only narrows the window.

**Fix now or separately.** Now (small, mechanical) — but only meaningful with C1.

## H3. Filing-time validators re-run at decision time and can block both Approve and Reject (the 21 Sep Attendance Request class, unfixed for the other six)

**Problem.** `decide()` sets the decision field and calls `doc.submit()` in one save
(`approval.py:295-300`), so every `validate()` check written for FILING runs again with
the approver's session and today's date. `hrms/tests/test_attendance_request_decision_is_always_possible.py`
fixed exactly this for one check on one doctype (`validate_no_attendance_to_create`).
The same shape remains on:

* Leave Application `validate()` (`leave_application.py:85-105`): `validate_attendance`
  (`:669-694`, throws if Attendance is Present/WFH on the leave dates — punches or the
  mirror mark days Present between filing and decision), `validate_balance_leaves`,
  `validate_salary_processed_days`, `block_transaction_after_relieving`,
  `validate_active_employee`, `validate_max_days`, `validate_dates_across_allocation`.
  A REJECT hits the same wall (rejecting is the same save).
* Shift Request `validate_approver` (`shift_request.py:100-115`): if the department
  approver table changed since filing, the named approver can no longer decide.
* OT Request / Attendance Request `validate_mandatory_attachment` runs in `on_submit`
  for a rejection too (`ot_request.py:230`, `attendance_request.py:166,181-200`): you
  cannot reject a request that lacks the attachment you would refuse it for.
* Leave `validate_leave_approver` mandatory check at `docstatus == 1` (`:945-953`) —
  correct by design, but the approver gets the refusal, not the employee.

**Location.** `hrms/api/approval.py:295-300`; controllers as listed.

**Root cause.** No distinction between "is this request well-formed" and "may this
decision be recorded". The AR fix drew that line for one validator only.

**User impact.** Approver taps Approve, reads a red toast ("Attendance for employee X is
already marked for…", "Insufficient leave balance", "Salary already processed…"), the
request stays Open — for both Approve and Reject — and sits in the queue. Combined with
C1 the employee sees "Open" and the approver remembers tapping Approve. This is the
second plausible mechanism for the reported symptom and unlike C1 it leaves the DB Open.

**Evidence.**
```
approval.py:295-300   doc.set(fieldname, status)
                      # ONE save cycle: validate -> before_submit -> … -> on_submit
                      doc.submit()
leave_application.py:669-694  def validate_attendance(self): … frappe.throw(_("Attendance for employee {0} is already marked …
attendance_request.py:164-166 def on_submit(self): self.validate_for_self_approval(); self.validate_mandatory_attachment()
```

**Recommended change.** Per doctype, gate filing-only validators on "undecided" (the AR
pattern: `if self.status != pending: return`), and never block a REJECT on evidence
requirements. Add a table-driven test: for each `DECIDE_THEN_SUBMIT` doctype, a
pending request with (a) Present attendance on its dates, (b) missing attachment, can
still be Rejected. Keep money/ledger checks (balance, salary processed) on Approve only
and make their refusal say what the approver must do.

**Fix now or separately.** Separately, one slice per doctype (each touches a
controller's validate chain); Leave `validate_attendance` first — it is the one that
occurs naturally as days pass.

## H4. A decided draft (status=Approved, docstatus=0) looks fully approved to the employee and fires the "Approved" notification

**Problem.** Desk still exposes the `status` Select (permlevel 1) on Leave Application
and `approval_status` on Expense Claim; Save with status=Approved is a normal save. Frappe
re-adds Save on dirty (`frappe/public/js/frappe/form/toolbar.js:850-862`), so
`request_approval.js:97 clear_primary_action()` does not remove that path. On that save:
* `on_update` → `notify_approval_status()` (`leave_application.py:128-136`,
  `pwa_notifications.py:14-36`) sends "Your Leave Application … has been **Approved**"
  — before any ledger entry exists.
* `get_leave_applications` returns no `docstatus` (`hrms/api/__init__.py:1065-1082`), so
  `LeaveRequestItem.vue:47` renders "Approved" (success chip) for a draft.
* `FormView.vue:543-552` shows `status` — "Approved" — with no "not yet submitted" cue.
* Meanwhile `report_half_transitioned` (`approval.py:376-403`) exists precisely because
  these rows accumulate, and nothing calls it from any UI.

**Location.** As above; `hrms/hr/doctype/leave_application/leave_application.json`
(`status` permlevel 1, writable); `hrms/hr/doctype/expense_claim/expense_claim.json`
(`approval_status` permlevel 1).

**Root cause.** Two decision paths coexist on Desk: `decide` (atomic) and plain Save
(field only). The notification and the chip key off the field, not the transition.

**User impact.** Employee is told "Approved", plans the leave, balance is never deducted,
attendance is never marked; HR later finds "Approved but draft" rows. Opposite polarity
from the reported symptom but same family (display ≠ transaction).

**Evidence.**
```
leave_application.py:128-136  def on_update(self): … self.publish_update(); self.notify_approval_status()
pwa_notifications.py:19       if self.has_value_changed(status_field) and status in ["Approved", "Rejected"]:
__init__.py:1065-1082         fields = ["name", "posting_date", …, "status", …]   # no docstatus
LeaveRequestItem.vue:47       return props.workflowStateField ? … : props.doc.status
```

**Recommended change.** (1) `notify_approval_status` only when `docstatus == 1` (move
the call into `on_submit` for Leave/Expense/Shift as OT/AR/RL/Comp already do). (2)
Return `docstatus` from `get_leave_applications`/`get_shift_requests` and derive the chip
through one helper (`requestStatusChip` already exists — extend it with the pending
value per doctype) so a decided draft renders "Approved · awaiting submit" or simply
"Open". (3) On Desk, `set_df_property("status","read_only",1)` when
`hrms.approval` decision buttons are offered, leaving Save for other edits.

**Fix now or separately.** (1) and (2) now — small and they close the notification lie;
(3) separately (Desk UX ruling).

---

# Medium

## M1. Silent no-op taps in the action sheet

**Problem.** `updateDocumentStatus` returns without any feedback when `submitting`,
when the captured review differs from `currentRequest()`, or when
`hasPermission(approve|reject|submit)` is momentarily false (the capability resource
re-fetches on every `doc.status` change and returns `[]` while loading —
`decisionCapability.js:50-62`).
**Location.** `frontend/src/components/RequestActionSheet.vue:532-541`;
`frontend/src/composables/decisionCapability.js:23-49,50-62`.
**Root cause.** Guard-and-return with no toast/log.
**User impact.** Approver taps Approve, nothing happens, no spinner, no message. A
second tap usually works; some approvers walk away believing the first tap took.
**Evidence.**
```
RequestActionSheet.vue:533-541  if ( submitting.value || review.doctype !== … || (status && !hasPermission(…)) ) return
```
**Recommended change.** `console.warn` + a neutral toast ("Still checking this request —
try again") on the refused-tap branch; disable the buttons while
`decisionCapability` is loading (expose `loading` from the composable).
**Fix.** Now (few lines).

## M2. `hrms:refetch_resource` is addressed by raw `Employee.user_id`; case drift or empty user_id misroutes it

**Problem.** `publish_update` publishes to `user:<Employee.user_id>` verbatim
(`leave_application.py:181-182`, `hrms/__init__.py:9-20`, `frappe/realtime.py:65-66`).
Socket rooms are exact-case strings (`realtime/handlers.js:146`). `hrms/utils/identity.py:20-23`
documents that `user_id` written by the mirror "goes through `frappe.db.set_value`,
which does not [lowercase], so case drift is reachable". An empty `user_id` makes
`refetch_resource(key, None)` fall back to `frappe.session.user` — the approver.
**Location.** `hrms/__init__.py:15-20`; every `publish_update`.
**User impact.** For a drifted employee the C1 channel never fires at all.
**Recommended change.** `normalize_login()` the target in `hrms.refetch_resource`, and
skip publishing when there is no user rather than defaulting to the session.
**Fix.** With C1/H2.

## M3. Attendance Request history list has no `status` column → submitted rows render an empty chip

**Problem.** `AttendanceRequestList.vue:19` requests
`["name","reason","from_date","to_date","docstatus"]`; `AttendanceRequestItem.vue:48`
returns `props.doc.status` when `docstatus` is truthy → `undefined` → `GStatusChip`
gets `status=undefined` (required String) and renders blank.
**Location.** `frontend/src/views/attendance/AttendanceRequestList.vue:19`;
`frontend/src/components/AttendanceRequestItem.vue:44-48`.
**User impact.** Employee cannot tell approved from rejected attendance requests in the
list; only the detail shows it. `OTRequestList.vue:17-25` got the same fix already
("status" added) — AR was missed.
**Recommended change.** Add `"status"` to the field list; extend
`request-status-chip.test.mjs`'s "every chip surface" test to AR.
**Fix.** Now (one line + test).

## M4. Three different "pending" labels for the same state, two of them wrong for their doctype

**Problem.** Draft rows are labelled by hand per item component:
* `ShiftRequestItem.vue:52` → `"Open"` (DB pending value is `Draft`; the list filter at
  `ShiftRequestList.vue:36` offers `Draft`, so filtering by Draft shows rows labelled Open).
  A decided draft (status Approved/Rejected, docstatus 0) also shows "Open".
* `AttendanceRequestItem.vue:48` → `"Draft"` (DB pending value is `Open`).
* `LeaveRequestItem.vue:47` → raw `status` (`Open`), including on decided drafts (H4).
* `OTRequestItem`/`ReplacementLeaveClaimItem` → `requestStatusChip` → `"Pending"`.
* `ExpenseClaimItem.vue:49-63` → composite `"Approved & Unpaid"` etc.
**Root cause.** No shared "pending label" — `requestStatusChip` exists but only two
surfaces use it.
**User impact.** Same request reads Open / Draft / Pending on three screens; filters and
labels disagree.
**Recommended change.** One `requestStatusChip(doc, doctype)` keyed on
`DECIDE_THEN_SUBMIT`'s pending value; every item component calls it (extend the existing
grep-test to all six components).
**Fix.** Separately (cosmetic, but it is the inventory the caller asked for).

## M5. `getFailureMessage` compares a raw status to a translated string

**Problem.** `status === __("Approved")` — in any non-English locale every failed
approval falls back to "Rejection failed!".
**Location.** `frontend/src/components/RequestActionSheet.vue:491-497`.
**Impact.** Only the fallback text (the server message wins when present).
**Fix.** Now, one-liner: compare to `"Approved"`.

## M6. Remote Checkin Request decision is not row-locked

**Problem.** `_decide` reads the row (`get_value`, no `for_update`), checks
`status != "Pending"`, then `get_doc` + `save()`. Two approvers (or two taps) can both
pass the Pending check; the second save's `before_save` sees the first only if it has
already committed. `on_update` side effects (late-checkout repair, employee notification)
can run twice.
**Location.** `hrms/api/remote_checkin.py:340-352`;
`hrms/hr/doctype/remote_checkin_request/remote_checkin_request.py:28-56`.
**Impact.** Low probability; duplicate notification / repair job. Contrast
`approval.py:246-259` which locks first.
**Fix.** Separately: `get_value(..., for_update=True)` before the status check, and
treat an already-decided same decision as idempotent success like `decide`.

## M7. Team tab visibility and decision routing disagree (sight ≠ action)

Already recorded in `audit-2026-09-13-approver.md` (c)B. Restated only for the lifecycle
table: `get_filters(for_approval)` shows Leave/Expense/Shift to the **named approver**
only (`hrms/api/__init__.py:961-971`), while `_is_routed_approver` also accepts HR
(fenced) and the `reports_to` manager (`approval.py:79-116`). A reports_to manager gets
the push notification, can decide from the notification's detail page, but never sees the
row in Team Requests. **Fix.** Separately, per the ticket.

## M8. Approver's own list after a decision depends on the same fragile channels

After `decide` succeeds the sheet only reloads the document (`RequestActionSheet.vue:559-566`);
the Team row is dropped by `list_update` or `hrms:team_*` (which `refetch_resource`
sends to the **session user** — `hrms/__init__.py:18` — i.e. the actor, so other
approvers/HR never get it). With H1 the approver's queue keeps showing an already
approved request; a second tap returns the idempotent no-op "Approved successfully!"
(`approval.py:276-282`) — harmless but confusing. **Fix.** With C1: reload
`team*`/`history*` in the sheet's `onSuccess`.

---

# Low

## L1. `submitting` still references `document.setValue?.loading`
`RequestActionSheet.vue:352-354` — `setValue` is no longer used by the sheet (finalize
replaced it). Dead term. Delete.

## L2. `FormView` computes `statusColor` that no template uses, costing one API call per detail open
`FormView.vue:508,600-605` → `guessStatusColor` → `hrms.api.get_doctype_states`
(`composables/index.js:77-83`). `GStatusChip` owns colour now. Delete the ref, the
watcher and (if unused elsewhere) the composable + endpoint.

## L3. `can_decide` has no production caller
`approval.py:342-349`; only `test_decision_access*.py` call it. Keep only if the
property test is worth its cost; otherwise delete and point the test at
`get_decision_actions`.

## L4. `report_half_transitioned` has no UI
`approval.py:375-403`. HR cannot reach it; the rows it lists are H4's output. Either a
Desk report/page or delete once H4 closes the path.

## L5. Six copies of "which field holds the decision / who approves"
`approval.py:37-41 APPROVER_FIELD` · `pwa_notifications.py:91-95 APPROVER_FIELD` ·
`hrms/api/__init__.py:925 APPROVER_FIELD_MAP` · `approval.py:119-136 DECIDE_THEN_SUBMIT` ·
`approved_request_guard.py:81-92 DECISION_FIELD_BY_DOCTYPE` ·
`pwa_notifications.py:58-66 APPROVAL_STATUS_FIELD` · frontend `RequestActionSheet.vue:479-481`,
`cancelRule.js:23`, `hrms/api/__init__.py:956` · Desk `request_approval.js:18-26`.
Two are pinned by tests (Desk list, guard map). The ticket-approval-refactor's
`DecisionPolicy` table is the right home; note here so the refactor scope is complete.

## L6. `historyRequests` excludes AR/OT/RL with an outdated comment
`RequestPanel.vue:96-102` says they are "docstatus-driven (no status/approver field)" —
false since 26 Aug. The real reason is `get_filters(history)` cannot scope them to "decided
by me" (`APPROVER_FIELD_MAP` lacks them, `__init__.py:958-959`). Fix the comment; add a
`decided_by` scope if the History tab should cover them.

## L7. `hrms.refetch_resource(key)` without `user` targets the actor, not "everyone"
`hrms/__init__.py:18` `user=user or frappe.session.user`. Every `"hrms:team_*"` call
therefore reaches only the person who just saved. Either document it or publish to the
doctype room. Not a defect today because `list_update` covers the team lists.

## L8. `frappe.client.get_doc_permissions` and `get_decision_actions` are both fetched per sheet open
`RequestActionSheet.vue:322-337`. `docPermissions` is only used for `cancel`/`delete`
booleans. Could be folded into `get_decision_actions` (returns `cancel` too). Cosmetic.

## L9. Employee Advance / Travel Request
Cited: `ticket-unfenced-self-submission.md`. Nothing new: both remain
`DECISION_FIELD_BY_DOCTYPE` members with `None` and outside every decision/notification
path; neither has a PWA surface.

---

# Answers to the eight questions

**1. State set and transitions** — Appendix A.

**2. Multi-level approval.** No. No Workflow fixture ships (`grep '"doctype": "Workflow"' hrms` →
none); if a site configures one, `_decision_access` returns `None`
(`approval.py:176-177`), `decide`/`finalize` refuse, and the PWA switches to
`WorkflowActionSheet` (`RequestActionSheet.vue:109-114`, `composables/workflow.js`). Every
`DECIDE_THEN_SUBMIT` doctype has exactly one decision (one field, one submit). Expense
Claim has a second *stage* (payment: `status` Unpaid→Paid via Payment Entry) but it is
not an approval. **"Open" never means "approved by one, waiting for another."** "Open"
means docstatus 0 and nobody has decided — or (H4) the field says Approved and the
transaction never ran, in which case the chip does not say Open anyway.

**3. Status mapping inventory** — Appendix B.

**4. How the employee's list/detail obtains status, and what makes it stale.**
* Home My Requests / Leave dashboard / Attendance dashboard / Expense dashboard: module-scope
  `hrms.api.get_*` resources with idb cache; refreshed only by `hrms:refetch_resource`
  (C1, H1, H2, M2). On cold start the idb copy paints first, then the fetch replaces it
  (`frappe-ui/src/resources/resources.js:196-203`).
* Leave History / OT list etc. (`ListView.vue`): `frappe.desk.reportview.get` on mount,
  on tab change, on pull-to-refresh, and on `list_update` (doctype room) — fresh.
* Detail (`FormView.vue:707,1042-1046`): `createDocumentResource` (`frappe.client.get`),
  fetched on mount (cached by [doctype,name] with `auto` → reload on re-open) — fresh.
* Socket subscriptions: `list_update` via `useListUpdate` (doctype rooms, permission
  checked server-side); no `doc_update` subscription anywhere; `hrms:refetch_resource`
  (user room); `hrms:remote_checkin_request` (user room).
* No optimistic updates in the decision path (`decide` result → `document.reload()`).
* Service worker: `frontend/public/sw.js` precaches build assets only; no runtime caching
  of `/api/method/*`. Not a staleness source.
* Desk-side paths emit exactly what the PWA listens to (the controllers' `publish_update`
  run for Desk saves too); the Desk Save-only path (H4) emits *and* notifies without a
  transition.

**5. Atomicity / divergence / idempotency.**
* `decide`/`finalize`: row lock before the state read (`approval.py:246-259,451-454`),
  one `doc.submit()`/`doc.cancel()` in the request transaction; any raise rolls back.
  Same-decision retry on a submitted doc returns the state without touching it
  (`:276-282`, `:517-519`); opposite decision → ValidationError. `expected_modified`
  guards stale reviews (`:313-322`). Push notifications are enqueued
  `enqueue_after_commit` and re-read the committed row (`pwa_notification.py:18-37,97-106`).
  Verdict: the PWA path cannot half-transition.
* Divergence IS reachable via Desk Save of the decision field (H4) — field=Approved,
  docstatus=0 — by any user with permlevel-1 write (Leave Approver / HR). The PWA's
  Submit button and Desk's "Submit" primary action (`request_approval.js:124-127`) exist to
  finish these; `report_half_transitioned` lists them.
* Remote Checkin Request: not locked (M6).
* OT Request locks Employee before the request to serialise RL grants
  (`approval.py:252-265`); RL-grant concurrency across *different* endpoints was noted as
  open on 13 Sep and is unchanged.

**6. Authorization gaps.** Everything found is already on record: ticket-approval-refactor
(policy shape), ticket-unfenced-self-submission (Advance/Travel), audit-2026-09-13
(reports_to manager can decide Leave/Expense/Shift named to another approver —
`approval.py:108-116` still applies reports_to to all doctypes; System Manager in
`_is_routed_approver:79`; OT row scope unfenced). New in this pass: none. The
`finalize` else-branch (`:466-513`) is reachable for any submittable doctype (no
allow-list) but requires native `submit`/`cancel` DocPerm there, so it widens nothing.

**7. Feedback after actions.** Success: one toast ("Approved successfully!") then the
sheet closes (`RequestActionSheet.vue:499-508,559-566`); the resulting chip depends on C1.
Failure: `onActionError` toasts the server's first message with HTML stripped
(`:510-524`, `loudRequest.js:78-83`); the fetcher-level toast is silenced for
`decide`/`finalize` (`loudRequest.js:59-61`, fixed 21 Sep) so there is exactly one.
Silent branches: M1 (refused tap), `decisionCapability` fetch failure only
`console.warn`s (`decisionCapability.js:46`) — the buttons simply never appear and the
approver sees a read-only sheet with no explanation. FormView's finalize path swallows
the rejection after toasting (`FormView.vue:931-938` `catch {}`) and reloads — acceptable.

**8. Dead / duplicated.** L1–L5, L8; `_state()` docstring still describes a KeyError bug
that no longer exists (`approval.py:205-218`) — comment rot only.

---

# Appendix A — transition table

Notation: `S` = decision field value, `D` = docstatus. "→ FE refresh" = what the PWA
reloads for the EMPLOYEE / the APPROVER after the mutation (given a live socket).

## Leave Application (`status`: Open | Approved | Rejected | Cancelled; permlevel 1)

| From | Action | Permission gate | Mutation | To | Side effects | Notification | FE refresh (employee / approver) |
|---|---|---|---|---|---|---|---|
| — | Employee files (PWA `insert` / Desk Save) | create DocPerm; `validate_filing_for_self`; `validate()` chain | insert | S=Open D=0 | `share_doc_with_approver` | `notify_approver` (after_insert) + email if HR Setting | `hrms:my_leaves`→employee, `hrms:team_leaves`→actor, `list_update` / list_update |
| Open/0 | Approve or Reject via `decide` (PWA sheet, Desk button) | `_decision_access`: read fence + company + self-policy + native-or-routed | `status=X; submit()` (one save) | S=X D=1 | on_submit: ledger entry, attendance, `validate_back_dated_application` | `notify_approval_status` (PWA Notification + push after commit) + email | `my_leaves`→employee, `team_leaves`→approver, `list_update` |
| Open/0 | Desk Save with status=Approved/Rejected (**no submit**) | permlevel-1 write | field only | S=X **D=0** | share; `publish_update` | **`notify_approval_status` fires** (H4) | same as above — chip shows Approved on a draft |
| Approved-or-Rejected/0 | Submit via `finalize(docstatus=1)` (PWA "Submit", Desk "Submit") | `_decision_access(doc, status)` | `submit()` | S=X D=1 | as decide | none new (status unchanged) | same |
| Open/0 | Employee withdraws (`hrms.api.withdraw_request`) | owner + D=0 | delete | gone | `after_delete → publish_update` | — | my/team |
| X/1 | Cancel via `finalize(docstatus=2)` (PWA Cancel, Desk Cancel) | native cancel DocPerm, else elevated when `is_approved_request && may_cancel` (own employee, HR-in-fence, named approver, reports_to); `block_cancel_of_approved` re-checks + payroll | `before_cancel: status=Cancelled; cancel()` | S=Cancelled D=2 | reverse ledger, cancel attendance | `notify_employee` email | `publish_update` in on_cancel |
| any/1 | Amend | cancel first | new doc `-1` | copy of fields | | | |
| X/1 | `decide` same X again | same gate | none | unchanged | — | — | returns state (idempotent) |
| X/1 | `decide` opposite | same gate | throws "already submitted as X" | unchanged | | | error toast |

Reachable combos: Open/0, Approved/0 (H4), Rejected/0 (H4), Approved/1, Rejected/1,
Cancelled/2. Unreachable by code: Open/1 (on_submit throws), Cancelled/0 except
`on_discard`.

## Expense Claim (`approval_status`: Draft | Approved | Rejected | Cancelled; `status`: Draft | Unpaid | Paid | Rejected | Submitted | Cancelled, read-only, derived)

Same rows as Leave with `Draft` as pending, `expense_approver`, `prevent_self_expense_approval`
and a second stage: Approved/1 → `status` Unpaid → Paid by Payment Entry/Journal (not an
approval). Chip composite "Approved & Unpaid". `validate_for_self_approval` runs in
`before_submit` only (`expense_claim.py:239-240`), so a Desk Save of approval_status by
the claimant is not refused until submit.

## Shift Request (`status`: Draft | Approved | Rejected)

Same rows, pending `Draft`, approver field `approver`, `validate_approver` at every
validate (H3), `validate_self_submission` at on_submit, Shift Assignment created on
Approved/1 and cancelled on cancel. Chip: "Open" for any D=0 (M4).

## OT Request / Attendance Request / Replacement Leave Claim / Compensatory Leave Request (`status`: Open | Approved | Rejected, read_only=1)

| From | Action | Gate | Mutation | To | Side effects | Notification | FE refresh |
|---|---|---|---|---|---|---|---|
| — | file | create + `validate_filing_for_self` | insert | Open/0 | | `notify_approver` (after_insert; OT/RL/AR route reports_to→HR) | AR: my/team keys; **OT/RL/Comp: nothing** (H2) |
| Open/0 | `decide` Approve/Reject | `_decision_access` (no HR-Settings self tickbox → own employee always refused) | set + submit | X/1 | Approved only: OT→RL allocation grant (Employee row locked first), AR→Attendance rows, RL→bank, Comp→Leave Allocation; Rejected → docstatus 1, nothing granted | `notify_approval_status` in on_submit | AR: keys + list_update; OT/RL/Comp: `list_update` only (team lists) |
| X/1 | `finalize` cancel | as Leave; OT additionally refused for everyone if paid on a submitted Salary Slip | cancel() | X/2 | reverse grant / attendance | | AR only |

Status is never writable by hand (read_only), so the H4 decided-draft state is reachable
only through `frappe.client.set_value`-style writes by a role that ignores read_only —
i.e. practically not.

## Remote Checkin Request (`status`: Pending | Approved | Rejected; not submittable)

| From | Action | Gate | Mutation | To | Side effects | Notification | FE refresh |
|---|---|---|---|---|---|---|---|
| — | punch outside geofence | employee | insert | Pending | | push+socket to approver (`_send_push`, after commit) | `hrms:remote_checkin_request`→approver; `pendingCountResource` |
| Pending | `approve`/`reject` | `may_decide` (HR-in-fence, approver on file, reports_to; never own) | `status=X; approved_at; save()` (**no row lock**, M6) | X | `propagate_approval_decision`: checkin flags, late-checkout repair | employee push/socket | approver reloads pending/decided/count explicitly (`RemoteApprovals.vue:340`); employee's CheckInPanel via `list_update` on Employee Checkin |
| X | change again | `before_save` throws "already decided" | | | | | |

## Employee Advance / Travel Request
Submitting IS approving; no decision field, no PWA surface, no self fence (ticket).

# Appendix B — status mapping inventory (frontend)

| Surface | File:line | Reads | Derivation | Drift vs backend |
|---|---|---|---|---|
| Leave row chip | `components/LeaveRequestItem.vue:47` | `status` (or workflow field) | raw | Approved-on-draft shows Approved (H4); no docstatus in payload |
| Shift row chip | `components/ShiftRequestItem.vue:52` | `docstatus`,`status` | `docstatus ? status : "Open"` | pending is `Draft` in DB; decided draft shows Open; filter offers Draft (M4) |
| Attendance row chip | `components/AttendanceRequestItem.vue:48` | `docstatus`,`status` | `docstatus ? status : "Draft"` | pending is `Open`; list view sends no `status` → blank chip (M3) |
| OT / RL row chip | `components/OTRequestItem.vue:53`, `ReplacementLeaveClaimItem.vue:55` → `utils/requestStatus.js:1-11` | `docstatus`,`status` | Cancelled / Rejected / Approved / Pending | consistent; only these two use the helper |
| Expense row chip | `components/ExpenseClaimItem.vue:49-63` | `approval_status`,`status` | composite "Approved & Unpaid" etc. | ok; unique vocabulary |
| Detail header chip | `components/FormView.vue:28-31,543-552` | workflow field → `status` → `approval_status` | raw | Approved-on-draft (H4) |
| Chip variants | `components/glass/GStatusChip.vue:42-66` | label | case-insensitive map, unknown→neutral | contains `open/pending/draft/unpaid` all as "attention"; no "approved & draft" cue beyond `progress` |
| Sheet action gating | `components/RequestActionSheet.vue:116-119,161-166,479-481` | `document.doc[approvalField]`, `docstatus` | `['Open','Draft']` = pending; `['Approved','Rejected']`+D0 = Submit | duplicates `DECIDE_THEN_SUBMIT` pending values by hand |
| Sheet cancel offer | `utils/cancelRule.js:22-25` | `docstatus`, decision field | "own"/"approved"/false | duplicates decision-field map |
| Capability | `composables/decisionCapability.js:12-21` | `docstatus`,`modified`,`status`,`approval_status` | server answers | ok |
| List filters | `views/leave/List.vue:35`, `views/attendance/ShiftRequestList.vue:36`, `views/expense_claim/List.vue:45,51` | literal option lists | hand-written | Leave omits Cancelled (fine: `docstatus != 2` filter), Shift uses Draft while chip says Open |
| History filter (server) | `hrms/api/__init__.py:950-960` | `status`/`approval_status` in (Approved, Rejected) | | AR/OT/RL/Comp excluded (L6) |
| For-approval filter (server) | `hrms/api/__init__.py:961-971` | `status = Open|Draft`, approver field | | named approver only; routing accepts more (M7) |
| Remote check-in | `views/RemoteApprovals.vue:52,282`, `views/Notifications.vue:213-218`, `components/CheckInPanel.vue:1166-1196` | `status` Pending/Approved/Rejected | raw | consistent |
| Desk decision buttons | `hrms/public/js/utils/request_approval.js:18-26,113-127` | `get_decision_actions` | server | pinned to Python map by `test_approval.py:74` |

Backend copies of the same maps: `approval.py:37-41,46,50-53,119-136`;
`approved_request_guard.py:55-73,81-92`; `pwa_notifications.py:58-66,91-95`;
`hrms/api/__init__.py:925 APPROVER_FIELD_MAP` and `get_filters:956`.
