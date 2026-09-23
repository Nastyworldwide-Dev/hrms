# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""What is waiting on the person asking (PWA Home, revamp §2).

Home's "Needs you" block has shipped since 2.0 rendering exactly ONE row type
— remote check-in approvals — because `home.needs_you` was never built and the
block read a single existing count. An approver with four leave applications
and an expense claim waiting saw nothing, which is worse than no block at all:
it is a block that looks authoritative and is wrong.

THE FENCE. Every count here goes through `approval._is_routed_approver`, the
same function `decide()` uses, applied per document. That is deliberate and it
is the whole design: a count derived from its own filter can disagree with the
list it opens, and an approver who is told "3 waiting" and finds two rows stops
trusting the number. Counting by asking the real authoriser is slower and
cannot drift.

Session-scoped by construction — no endpoint takes a user or employee.
"""

import logging

import frappe

from hrms.api.approval import DECIDE_THEN_SUBMIT, _is_routed_approver, _request_read_allowed

logger = logging.getLogger(__name__)

#: How many candidate documents are examined per type before the count is
#: reported as "many". A routed-approver check is a per-document call, and an
#: HR operator on a large site is routed everything — so an unbounded scan
#: would make Home's first paint wait on thousands of permission checks.
#:
#: The cap is a DISPLAY bound, not a correctness one: past it the block says
#: "20+", which is the same decision an approver makes anyway (this is a big
#: queue, open it).
SCAN_CAP = 20

#: The employee's word for each type, and where tapping the row goes. The
#: doctype name never reaches a screen — "Attendance Request" is a table;
#: "attendance fixes" is what somebody is waiting for.
#: The route names are the PWA's own, and a name that does not exist throws at
#: the moment somebody taps — not at build, not in any other test. They are
#: pinned by frontend/src/views/__tests__/needs-you.test.js, which resolves
#: every one of them against the router.
ROW_COPY = {
	"Leave Application": ("leave request", "LeaveApplicationListView"),
	"Expense Claim": ("expense claim", "ExpenseClaimListView"),
	"Shift Request": ("shift request", "ShiftRequestListView"),
	"OT Request": ("overtime claim", "OTRequestListView"),
	"Attendance Request": ("attendance fix", "AttendanceRequestListView"),
	"Replacement Leave Claim": ("replacement leave claim", "ReplacementLeaveView"),
	# No list of its own in the PWA — comp leave surfaces with leave. Sending
	# somebody to a screen that does not show the thing they tapped is worse
	# than sending them to the nearest one that does.
	"Compensatory Leave Request": ("compensatory leave request", "LeaveApplicationListView"),
}


def _pending_for(doctype: str, field: str, pending: str) -> int:
	"""How many `doctype` rows are waiting on THIS caller.

	Pending means the decision field still says so AND the document is not
	submitted: `approval` treats docstatus 1 as decided whatever the field
	says, because that is when the consequence lands (the allocation, the
	attendance row, the banked hours).
	"""
	# `name` ONLY. Compensatory Leave Request has no `company` column, and
	# asking for one made that query raise — which the caller's except swallowed,
	# so six of the seven types silently reported zero on a site that had
	# pending rows. Found by running it against the bench; a per-doctype field
	# list is a promise about seven schemas that nothing was checking.
	candidates = frappe.get_all(
		doctype,
		filters={field: pending, "docstatus": 0},
		pluck="name",
		order_by="modified desc",
		limit=SCAN_CAP + 1,
		ignore_permissions=True,
	)
	if not candidates:
		return 0

	count = 0
	for name in candidates:
		# The full document, because `_is_routed_approver` reads whichever of
		# the approver field, the employee and the company THAT type has — and
		# the point of calling it is that this module does not need to know.
		# Read first, as approval.decide does: routing's HR branch admits System
		# Manager, whom approval_row_scope denies read (review of be4b81edf).
		doc = frappe.get_doc(doctype, name)
		if _request_read_allowed(doc) and _is_routed_approver(doc):
			count += 1
	return count


@frappe.whitelist(methods=["GET", "POST"])
def get_needs_you() -> dict:
	"""Everything waiting on the caller, one row per kind.

	Returns rows the PWA renders verbatim rather than a bag of counts: the
	COPY is a decision ("2 leave requests to approve", not "Leave Application:
	2") and making it here keeps it in one place instead of in every consumer.
	"""
	rows = []
	for doctype, (field, pending) in DECIDE_THEN_SUBMIT.items():
		if not frappe.db.table_exists(doctype.replace(" ", "")) and not frappe.db.exists("DocType", doctype):
			# A site without the app that owns a type must not 500 Home.
			continue
		try:
			count = _pending_for(doctype, field, pending)
		except Exception:
			# One unavailable type must not take the whole block down — Home is
			# the first screen and a 500 here is the app looking broken.
			#
			# But it is logged at EXCEPTION with the doctype named, because a
			# silent skip is how this very module reported zero for six of seven
			# types: the swallow was working exactly as intended and hiding a
			# real bug. A count that quietly becomes zero is worse than an error.
			logger.exception("[needs_you] %s failed; reported as zero", doctype)
			continue
		if not count:
			continue
		noun, route = ROW_COPY.get(doctype, (doctype.lower(), None))
		rows.append(
			{
				"key": doctype,
				"doctype": doctype,
				"count": min(count, SCAN_CAP),
				"capped": count > SCAN_CAP,
				"noun": noun,
				"route": route,
			}
		)

	total = sum(row["count"] for row in rows)
	logger.info("[needs_you] user=%s kinds=%d total=%d", frappe.session.user, len(rows), total)
	return {"rows": rows, "total": total}
