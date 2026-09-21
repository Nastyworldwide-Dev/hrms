# Family — fix(pwa): one status rule and buttons from the doc (21 Sep 2026)
CLASS: the phone decided a request's status and its buttons from hand-typed word lists in eight places; a Desk-saved "Approved" on an unsubmitted row read as Approved; a whole-doc JSON equality hid Approve/Reject on any local touch.
Changed: utils/requestStatus.js (ONE table mirroring api/approval.py DECIDE_THEN_SUBMIT: decision field + pending word per doctype; decided-but-docstatus-0 → pending word; Expense Claim infers docstatus from status), six *Item.vue + GStatusChip + FormView call it; RequestActionSheet Approve/Reject = isPending && hasPermission('approval'); decisionCapability edited-server-field check by VALUE (originalDoc is a JSON deep copy); api/__init__.py get_leave_applications sends docstatus.
frontend/src/views/ReplacementLeave.vue not-affected — calls requestStatusChip (kept wrapper), same row as OT
frontend/src/components/ListView.vue not-affected — generic list, no status chip of its own
frontend/src/components/AttendanceRequestList.vue ticket — its field list lacks "status" (M3, worker note); shows the raw row today as before
hrms/api/__init__.py get_expense_claims ticket — sends no docstatus; the PWA infers it from status (set_status writes Draft at docstatus 0), sound but a second source
frontend/src/components/CheckInPanel.vue / LateCheckoutDialog.vue not-affected — not request rows
