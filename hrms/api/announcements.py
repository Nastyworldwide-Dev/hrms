# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Announcements read API for the PWA.

Session-scoped BY CONSTRUCTION: no endpoint accepts an employee or a user
argument, so there is no shape in which one person can ask for another's
board or mark something read on their behalf. The audience fence is applied
here in code rather than trusted to a query filter, because a whitelisted
endpoint is the classic way a row-scope hook gets bypassed — the same
reasoning `hrms/api/sop.py` carries, and the same primitives.

Writes are limited to the two an EMPLOYEE performs about THEMSELVES: marking a
card read, and acknowledging one. HR creates and edits announcements through
the standard document API, gated by the DocType's permission matrix (any HR
User may publish — owner's ruling, 22 September 2026 — with `owner` carrying
the accountability rather than a maker-checker workflow nobody would use).
"""

import logging

import frappe
from frappe import _
from frappe.utils import now_datetime, nowdate

from hrms.utils.identity import own_employees

logger = logging.getLogger(__name__)

#: What the board needs to render a card. `body` is deliberately absent: the
#: list shows a title and a category, and a list endpoint that returns every
#: body is a payload that grows without limit as the board fills up.
LIST_FIELDS = (
	"name",
	"title",
	"category",
	"pinned",
	"acknowledge_required",
	"publish_from",
	"publish_until",
	"modified",
)

#: Home shows at most this many. A home screen is not a noticeboard — §2 of the
#: revamp puts announcements third, under the check-in, and a block that can
#: grow without bound pushes everything an employee came for below the fold.
HOME_LIMIT = 2


def _reader():
	"""The caller's own Employee row, or None.

	Fails closed the same way every other fence in this app does: no Active
	Employee means no board, not an unfiltered one. Resolved through the
	canonical identity primitive so an ambiguous or case-drifted `user_id`
	cannot hand back a different person's row.
	"""
	names = own_employees(frappe.session.user)
	if not names:
		logger.info("[announcements] no active employee for %s", frappe.session.user)
		return None
	return frappe.db.get_value(
		"Employee", names[0], ["name", "company", "department", "branch"], as_dict=True
	)


def audience_matches(audience, audience_value, reader) -> bool:
	"""Is this announcement addressed to this reader?

	Pure and separately testable on purpose: this is the whole fence, and a
	fence expressed only as a SQL filter is one nobody can exercise without a
	database. An unknown audience returns False — a new option added to the
	Select without a rule here must hide the announcement, never show it to
	everybody.
	"""
	if audience == "Everyone":
		return True
	if not audience_value:
		# A targeted announcement with no target is a misconfiguration. Showing
		# it to everyone is the failure mode that matters.
		return False
	if audience == "Company":
		return audience_value == reader.company
	if audience == "Department":
		return audience_value == reader.department
	if audience == "Branch":
		return audience_value == reader.branch
	logger.warning("[announcements] unknown audience %r — hidden", audience)
	return False


def _visible_rows(reader) -> list[dict]:
	"""Every announcement this reader may see today, pinned first then newest.

	The date window is applied in SQL because it is cheap and exact; the
	AUDIENCE is applied in Python because it reads across three different
	fields and an OR-chain of those in a filter is the kind of query that is
	silently wrong for one branch and nobody notices.
	"""
	from hrms.utils.timezone import employee_now

	# The reader's own day, not the server's: near midnight in another time
	# zone a notice appeared a day early or late (rule 66a5e6145).
	today = str(employee_now(reader.name).date())
	rows = frappe.get_all(
		"HR Announcement",
		filters={
			"published": 1,
			"publish_from": ("<=", today),
			"publish_until": (">=", today),
		},
		fields=[*LIST_FIELDS, "audience", "audience_value"],
		order_by="pinned desc, publish_from desc, modified desc",
		ignore_permissions=True,
	)
	visible = [row for row in rows if audience_matches(row.audience, row.audience_value, reader)]
	logger.info("[announcements] employee=%s live=%d visible=%d", reader.name, len(rows), len(visible))
	for row in visible:
		# The audience is HOW the fence decided, not something the reader needs
		# or is entitled to know — a department name is another team's business.
		row.pop("audience", None)
		row.pop("audience_value", None)
	return visible


def _read_state(employee: str, names: list[str]) -> dict[str, dict]:
	if not names:
		return {}
	rows = frappe.get_all(
		"HR Announcement Read",
		filters={"employee": employee, "announcement": ("in", names)},
		fields=["announcement", "read_on", "acknowledged"],
		ignore_permissions=True,
	)
	return {row.announcement: row for row in rows}


def _decorate(rows, employee):
	state = _read_state(employee, [row.name for row in rows])
	for row in rows:
		seen = state.get(row.name)
		row["read"] = bool(seen and seen.read_on)
		row["acknowledged"] = bool(seen and seen.acknowledged)
		# The one thing the card's behaviour turns on: an announcement that
		# asks for acknowledgement and has not had it stays put.
		row["needs_acknowledgement"] = bool(row.acknowledge_required) and not row["acknowledged"]
	return rows


@frappe.whitelist(methods=["GET", "POST"])
def list_announcements() -> dict:
	"""The full board for the session user."""
	reader = _reader()
	if not reader:
		return {"announcements": [], "unread": 0}
	rows = _decorate(_visible_rows(reader), reader.name)
	return {
		"announcements": rows,
		"unread": sum(1 for row in rows if not row["read"]),
	}


@frappe.whitelist(methods=["GET", "POST"])
def home_announcements() -> dict:
	"""At most two, for the Home block, plus how many more there are.

	Unread and unacknowledged first: the block is a summary, and a summary that
	leads with something already read wastes the only two slots it has.
	"""
	reader = _reader()
	if not reader:
		return {"announcements": [], "more": 0, "unread": 0}
	rows = _decorate(_visible_rows(reader), reader.name)
	ordered = sorted(
		rows,
		key=lambda row: (
			not row["needs_acknowledgement"],
			row["read"],
			not row["pinned"],
		),
	)
	shown = ordered[:HOME_LIMIT]
	return {
		"announcements": shown,
		"more": max(len(rows) - len(shown), 0),
		"unread": sum(1 for row in rows if not row["read"]),
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_announcement(name: str) -> dict:
	"""One announcement WITH its body, and it is marked read as a side effect.

	Opening a card is the read event — there is no separate "mark read" door,
	because one would be a door that can be called about an announcement the
	caller cannot see.
	"""
	# A whitelisted argument arrives as whatever the caller sent; a dict reaches
	# frappe.db.get_value as FILTERS rather than as a name. Narrowed at the
	# boundary, the same shape kpi.py refuses.
	if not isinstance(name, str) or not name.strip():
		frappe.throw(_("An announcement must be named."), frappe.PermissionError)
	name = name.strip()

	reader = _reader()
	if not reader:
		frappe.throw(_("Announcements are for employees."), frappe.PermissionError)

	visible = {row.name for row in _visible_rows(reader)}
	if name not in visible:
		# Same message whether it is missing, expired, unpublished or addressed
		# to somebody else: a different one for each would let a caller map the
		# board by probing it.
		logger.warning("[announcements] %s refused %s", frappe.session.user, name)
		frappe.throw(_("That announcement is not available."), frappe.PermissionError)

	doc = frappe.get_doc("HR Announcement", name)
	_record_read(name, reader.name)
	return {
		"name": doc.name,
		"title": doc.title,
		"category": doc.category,
		"body": doc.body,
		"pinned": bool(doc.pinned),
		"acknowledge_required": bool(doc.acknowledge_required),
		"publish_from": doc.publish_from,
		"publish_until": doc.publish_until,
		"acknowledged": bool(
			frappe.db.get_value(
				"HR Announcement Read",
				{"announcement": name, "employee": reader.name},
				"acknowledged",
			)
		),
	}


def _record_read(announcement: str, employee: str):
	"""Idempotent. Opening a card twice is not two readings, and the count HR
	reads off this has to be one somebody can trust."""
	existing = frappe.db.exists("HR Announcement Read", {"announcement": announcement, "employee": employee})
	if existing:
		return
	frappe.get_doc(
		{
			"doctype": "HR Announcement Read",
			"announcement": announcement,
			"employee": employee,
			"read_on": now_datetime(),
		}
	).insert(ignore_permissions=True)
	logger.info("[announcements] %s read by %s", announcement, employee)


@frappe.whitelist(methods=["POST"])
def acknowledge(name: str) -> dict:
	"""'I've read and understood this.'

	POST only: it is a statement a person makes about themselves and it goes in
	the record with their name and the time, which is the whole point of it for
	a policy or a safety notice.
	"""
	if not isinstance(name, str) or not name.strip():
		frappe.throw(_("An announcement must be named."), frappe.PermissionError)
	name = name.strip()

	reader = _reader()
	if not reader:
		frappe.throw(_("Announcements are for employees."), frappe.PermissionError)
	if name not in {row.name for row in _visible_rows(reader)}:
		logger.warning("[announcements] %s refused to acknowledge %s", frappe.session.user, name)
		frappe.throw(_("That announcement is not available."), frappe.PermissionError)

	if not frappe.db.get_value("HR Announcement", name, "acknowledge_required"):
		# Acknowledging something that never asked for it would put a
		# placeholder in the record and let a report claim compliance for a
		# notice that never had the requirement.
		frappe.throw(_("That announcement does not ask for acknowledgement."))

	_record_read(name, reader.name)
	row = frappe.db.get_value("HR Announcement Read", {"announcement": name, "employee": reader.name}, "name")
	frappe.db.set_value(
		"HR Announcement Read",
		row,
		{"acknowledged": 1, "acknowledged_on": now_datetime()},
		update_modified=False,
	)
	logger.info("[announcements] %s acknowledged by %s", name, reader.name)
	return {"acknowledged": True}


# ---------------------------------------------------------------------------
# HR's side. The plan named exactly one report — "read by 31 of 44" — because
# it is the only one anybody asks for: did the notice land. Without it HR
# publishes into silence and cannot tell a notice nobody read from a notice
# nobody needed.
#
# HR-ONLY, and checked here rather than trusted to the Desk form. The reach of
# an announcement is a roster fact — how many people are in a department, who
# has not read something — and an employee has no business with it.


def _require_hr():
	from hrms.hr.utils import is_hr_operator

	if not is_hr_operator(frappe.session.user):
		logger.warning("[announcements] reach refused for %s", frappe.session.user)
		frappe.throw(_("Announcement reach is for HR."), frappe.PermissionError)


def _audience_employees(doc) -> list[str]:
	"""Everyone this announcement is addressed to.

	The SAME rule the PWA fence uses — `audience_matches`, inverted from "may
	this reader see it" to "who are the readers". Two implementations of the
	audience would give HR a denominator that disagrees with who actually gets
	the card, and the number's whole value is that it is trustworthy.
	"""
	filters = {"status": "Active"}
	if doc.audience == "Company":
		filters["company"] = doc.audience_value
	elif doc.audience == "Department":
		filters["department"] = doc.audience_value
	elif doc.audience == "Branch":
		filters["branch"] = doc.audience_value
	return frappe.get_all("Employee", filters=filters, pluck="name", ignore_permissions=True)


@frappe.whitelist(methods=["GET", "POST"])
def get_reach(name: str) -> dict:
	"""Did it land. Two numbers and, for a policy, a third."""
	_require_hr()
	if not isinstance(name, str) or not name.strip():
		frappe.throw(_("An announcement must be named."), frappe.PermissionError)

	doc = frappe.get_doc("HR Announcement", name.strip())
	audience = _audience_employees(doc)
	rows = frappe.get_all(
		"HR Announcement Read",
		filters={"announcement": doc.name},
		fields=["employee", "acknowledged"],
		ignore_permissions=True,
	)
	# Counted against the CURRENT audience: somebody who has left, or moved
	# department since reading, is not part of "31 of 44" any more. Otherwise
	# the numerator can exceed the denominator, which makes the whole line
	# untrustworthy the first time HR sees it.
	in_audience = set(audience)
	read = [row for row in rows if row.employee in in_audience]

	logger.info("[announcements] reach %s: %d read of %d", doc.name, len(read), len(audience))
	return {
		"audience_count": len(audience),
		"read_count": len(read),
		"acknowledged_count": sum(1 for row in read if row.acknowledged),
		"acknowledge_required": bool(doc.acknowledge_required),
		"published": bool(doc.published),
	}


@frappe.whitelist(methods=["GET", "POST"])
def get_outstanding(name: str) -> list[str]:
	"""Who has not confirmed, by name, so HR can chase them.

	Only for announcements that ASK for confirmation. On an ordinary notice
	this would be a list of everybody who has not happened to open the app,
	which is not a thing anybody should be chased about.
	"""
	_require_hr()
	if not isinstance(name, str) or not name.strip():
		frappe.throw(_("An announcement must be named."), frappe.PermissionError)

	doc = frappe.get_doc("HR Announcement", name.strip())
	if not doc.acknowledge_required:
		frappe.throw(_("That announcement does not ask for confirmation."))

	audience = _audience_employees(doc)
	confirmed = set(
		frappe.get_all(
			"HR Announcement Read",
			filters={"announcement": doc.name, "acknowledged": 1},
			pluck="employee",
			ignore_permissions=True,
		)
	)
	outstanding = [name for name in audience if name not in confirmed]
	if not outstanding:
		return []
	return frappe.get_all(
		"Employee",
		filters={"name": ("in", outstanding)},
		pluck="employee_name",
		order_by="employee_name asc",
		ignore_permissions=True,
	)
