# Ticket: Desk wording for Expense Claim and Remote Checkin Request

Done 5 Oct 2026 (commit "one word per state in Desk"): Leave, OT, Shift, Attendance Request, Replacement Leave Claim,
Compensatory Leave Request say Waiting / Approved / Rejected / Cancelled, like Nadi.

DONE 2026-10-07 (commit pending; the list scripts themselves landed 5 Oct in 2110f2ec7, 3f761024f, 6976d80c0):
(1) Expense Claim: expense_claim_list.js get_indicator says Waiting / Approved · unpaid / Paid / Rejected / Cancelled,
the same words as Nadi. Owner ruling E1a (7 Oct 2026) settled the wording. No doctype JSON change and no patch: the doctype
"states" list is already empty, and the Desk LIST pill comes from get_indicator (plan amendment P2).
(2) Remote Checkin Request: remote_checkin_request_list.js says Waiting where the stored word is Pending.
7 Oct added the proof: both tests now ask Nadi's own rule (frontend/src/utils/requestStatus.js, imported by node) for the
same document and assert the Desk word equals it, so the two cannot drift apart again.
Known and deliberate: Nadi greys a cancelled request, every Desk request list paints it red.

LIVE CHECK (cannot be seen from the repo): a Workflow record created on the site for any of the six doctypes draws its
own state word BEFORE the list script (frappe.get_indicator order: workflow, doctype states, listview get_indicator).
After deploy, open the Leave Application list as HR: the pill must say Waiting / Approved. If it still says Draft or Open, look
at Workflow List for that doctype.
