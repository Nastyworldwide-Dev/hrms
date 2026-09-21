CLASS: a surface carrying its own private copy of "what state is this request
in". utils/requestStatus.js was made the one rule on 21 Sep (527baf268) and six
item components joined it; two surfaces never did, and two Employee Issue
states had no entry in the variant table, so a finished issue rendered the same
grey as an untouched one. On top of that the rule faithfully reported three
different pending words — Open, Draft, Pending — for one state, so a staff
member reading two of their own requests side by side saw two words.

Instance test: frontend/src/utils/__tests__/requestStatus.test.js
  "a remote check-in row reads the same rule as every other request"
Invariant test: same file — "a decided draft is still pending and says ONE
  waiting word" walks the whole doctype table, and "the stored pending word is
  never rewritten" pins that this is a display change, not a migration.

Call sites of requestStatus / requestStatusChip / chipVariant / GStatusChip:

frontend/src/utils/requestStatus.js same-root — the rule itself; WAITING, the
  Remote Checkin Request row and the two Employee Issue variants.
frontend/src/views/RemoteApprovals.vue:49 same-root — the hand-rolled chip,
  replaced by GStatusChip; this is the defect instance.
frontend/src/components/LeaveRequestItem.vue:49 same-root — reads .label, now
  "Waiting" while pending. Display only.
frontend/src/components/AttendanceRequestItem.vue:47 same-root — same.
frontend/src/components/OTRequestItem.vue:54 same-root — same.
frontend/src/components/ReplacementLeaveClaimItem.vue:56 same-root — same.
frontend/src/components/ShiftRequestItem.vue:53 same-root — same; this is the
  row that used to say "Draft" against a list filter offering "Draft".
frontend/src/components/ExpenseClaimItem.vue:54 same-root — same; its submitted
  composite ("Approved & Unpaid") is untouched.
frontend/src/components/FormView.vue:552 same-root — the detail header; a
  workflow state field still wins over the rule, unchanged.
frontend/src/components/RequestActionSheet.vue:259 same-root — the review sheet
  reads .pending to decide whether to offer buttons; .pending is unchanged.
frontend/src/views/ot/OTRequestForm.vue:193 same-root — statusLabel, the word
  only.
frontend/src/views/ot/ReplacementLeave.vue:86 same-root — same.
frontend/src/components/glass/GStatusChip.vue:44 same-root — chipVariant; the
  two new Employee Issue keys reach every chip through it.
frontend/src/views/issues/IssueList.vue:45 same-root — renders the raw Employee
  Issue status; it now gets colour without changing this file.

Not affected:
Every server word. hrms/api/approval.py DECIDE_THEN_SUBMIT, the doctype JSON
  Select options and hrms/api/__init__.py get_filters() keep Open / Draft /
  Pending exactly as stored. No list filter, no report and no existing row
  changes. Pinned by the "stored pending word is never rewritten" test.
frontend/src/utils/helpdesk.js — already renames at display time (statusLabel,
  "Replied" -> "Awaiting you"); the precedent this slice follows, unchanged.
