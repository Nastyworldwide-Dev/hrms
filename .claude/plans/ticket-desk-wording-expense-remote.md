# Ticket: Desk wording for Expense Claim and Remote Checkin Request

Done 5 Oct 2026 (commit "one word per state in Desk"): Leave, OT, Shift, Attendance Request, Replacement Leave Claim,
Compensatory Leave Request say Waiting / Approved / Rejected / Cancelled, like Nadi.

LEFT: (1) Expense Claim has two axes: Frappe's doctype "states" (Draft, Submitted, Paid, Unpaid, Rejected, Cancelled) draw its
indicator before any list script can, and Nadi says "Approved · unpaid". Change the states rows in the doctype JSON, with a
guarded patch (property-setter-shadows-doctype-json). (2) Remote Checkin Request is not submittable: Desk says Pending, Nadi says
Waiting. Add a *_list.js whose indicator maps Pending to Waiting.
DO AFTER: Nabil's word on the Expense wording.

LIVE CHECK (cannot be seen from the repo): a Workflow record created on the site for any of the six doctypes draws its
own state word BEFORE the list script (frappe.get_indicator order: workflow, doctype states, listview get_indicator).
After deploy, open the Leave Application list as HR: the pill must say Waiting / Approved. If it still says Draft or Open, look
at Workflow List for that doctype.
