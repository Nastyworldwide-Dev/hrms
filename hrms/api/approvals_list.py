"""Everything waiting on the caller's decision, as rows (the Approvals page).

Owner ruling, 23 Sep 2026: approvals appear only where they can be done, and
the Approvals page is that place (audit-flows 4B, AUDIT-PLAN P1-B). Home's
Waiting on you gives counts; this gives the rows behind them, oldest first,
each saying who, what, when and why, in the person's words.

A row is listed only when the caller may READ it (`_request_read_allowed`) and
it is routed to them (`_is_routed_approver`) — the two gates `approval.decide`
applies, in its order. Routing alone is not enough: its HR branch admits
System Manager, whom `approval_row_scope` deliberately denies read, so an
admin-only login saw every team's requests and reasons (review of be4b81edf).
Session-scoped: the caller is never a parameter.
"""

import logging
import re
from datetime import date, datetime

import frappe

from hrms.api.approval import APPROVER_FIELD, DECIDE_THEN_SUBMIT, _is_routed_approver, _request_read_allowed
from hrms.utils.identity import normalize_login, own_employees

logger = logging.getLogger(__name__)

#: Rows examined per type before the list stops (the same bound needs_you
#: uses): an HR operator is routed everything, and every candidate costs a
#: routed-approver check. Past it the page says the list is longer.
SCAN_CAP = 50

#: The person's word for each type (glossary: "Time off", "Overtime" …).
KIND = {
	"Leave Application": "Time off",
	"Expense Claim": "Expense",
	"Shift Request": "Shift change",
	"Attendance Request": "Fix a day",
	"OT Request": "Overtime",
	"Replacement Leave Claim": "Replacement leave",
	"Compensatory Leave Request": "Time off in lieu",
}


def _types_on_site() -> list[str]:
	"""Request types this site has; a missing app must not 500 the page."""
	return [dt for dt in DECIDE_THEN_SUBMIT if frappe.db.exists("DocType", dt)]


def _hours(hours) -> str:
	minutes = round((float(hours or 0)) * 60)
	h, m = divmod(minutes, 60)
	return f"{h}h {m:02d}m" if h else f"{m}m"


def _days(n) -> str:
	n = float(n or 0)
	text = f"{n:g}"
	return f"{text} day" if n == 1 else f"{text} days"


#: Where a row sits on the page (owner-approved design, 23 Sep 2026). YOURS =
#: sent to the caller; OTHER = they receive it only because they are higher up
#: the chain, or HR. Presentation only: the two gates in `_mine_of` decide
#: which rows exist; this never admits or drops one.
YOURS, OTHER = "yours", "other"

#: The Employee-record field naming who a request type is sent to. Remote
#: check-ins are a shift matter; everything else goes to the leave approver.
RECORD_APPROVER_FIELD = {"Remote Checkin Request": "shift_request_approver"}

#: "Production - NSTY" -> "Production": ERPNext suffixes each department with
#: its company abbreviation, which is noise on a phone.
_COMPANY_SUFFIX = re.compile(r"\s+-\s+[^-]+$")


def _me() -> dict:
	"""The caller, as the two things "sent to me" compares against."""
	user = frappe.session.user
	mine = own_employees(user)
	return {"login": normalize_login(user), "employee": mine[0] if mine else None}


def _employee_facts(employee, cache: dict) -> dict:
	"""The routing and department fields of one employee, read once per call."""
	if not employee:
		return {}
	if employee not in cache:
		facts = frappe.db.get_value(
			"Employee",
			employee,
			["department", "leave_approver", "shift_request_approver", "reports_to"],
			as_dict=True,
		)
		if not isinstance(facts, dict):
			logger.warning("[approvals_list] no Employee record for %s; grouped as unknown", employee)
			facts = {}
		cache[employee] = facts
	return cache[employee]


def _sent_to_me(doctype: str, doc, facts: dict, me: dict) -> bool:
	"""Is this request addressed to the caller, rather than merely visible?

	The request's own approver field, the approver named on the employee's
	record, or the employee reports to the caller's own employee.
	"""
	if not me["login"]:
		return False
	field = APPROVER_FIELD.get(doctype) or ("approver" if doctype == "Remote Checkin Request" else None)
	if field and normalize_login(doc.get(field)) == me["login"]:
		return True
	if normalize_login(facts.get(RECORD_APPROVER_FIELD.get(doctype, "leave_approver"))) == me["login"]:
		return True
	return bool(me["employee"]) and facts.get("reports_to") == me["employee"]


def _team_approver_name(facts: dict) -> str:
	"""Whose team: the leave approver's full name, else the manager's name."""
	name = ""
	if login := facts.get("leave_approver"):
		name = frappe.db.get_value("User", login, "full_name") or login
	elif manager := facts.get("reports_to"):
		name = frappe.db.get_value("Employee", manager, "employee_name") or manager
	logger.debug("[approvals_list] team approver resolved: %s", "named" if name else "none")
	return name


def _placement(doctype: str, doc, me: dict, cache: dict) -> dict:
	"""`section`, `department` and `approver_name` for one row."""
	facts = _employee_facts(doc.get("employee"), cache)
	mine = _sent_to_me(doctype, doc, facts, me)
	department = facts.get("department")
	logger.debug("[approvals_list] %s %s -> %s", doctype, doc.get("name"), YOURS if mine else OTHER)
	return {
		"section": YOURS if mine else OTHER,
		"department": _COMPANY_SUFFIX.sub("", department) if isinstance(department, str) else "",
		"approver_name": "" if mine else _team_approver_name(facts),
	}


def _row(doc, me: dict | None = None, cache: dict | None = None) -> dict:
	"""What an approver needs to decide, in plain words. No raw field names."""
	kind = KIND.get(doc.doctype, doc.doctype)
	when, detail, reason = "", "", ""
	if doc.doctype == "Leave Application":
		when = _range(doc.get("from_date"), doc.get("to_date"))
		detail = f"{doc.get('leave_type')} · {_days(doc.get('total_leave_days'))}"
		reason = doc.get("description") or ""
	elif doc.doctype == "OT Request":
		when = _day(doc.get("ot_date"))
		detail = _hours(doc.get("claimed_hours"))
		reason = doc.get("explanation") or ""
	elif doc.doctype == "Expense Claim":
		detail = f"{frappe.utils.fmt_money(doc.get('grand_total') or doc.get('total_claimed_amount') or 0)}"
		reason = doc.get("remark") or ""
	elif doc.doctype == "Shift Request":
		when = _range(doc.get("from_date"), doc.get("to_date"))
		detail = doc.get("shift_type") or ""
	elif doc.doctype == "Attendance Request":
		when = _range(doc.get("from_date"), doc.get("to_date"))
		detail = doc.get("reason") or ""
		reason = doc.get("explanation") or ""
	elif doc.doctype == "Replacement Leave Claim":
		when = f"{date.fromisoformat(str(doc.bank_month)[:10]):%B %Y}" if doc.get("bank_month") else ""
		detail = _days(doc.get("claimed_days"))
		reason = doc.get("explanation") or ""
	elif doc.doctype == "Compensatory Leave Request":
		when = _range(doc.get("work_from_date"), doc.get("work_end_date"))
		detail = doc.get("leave_type") or ""
		reason = doc.get("reason") or ""
	return {
		"doctype": doc.doctype,
		"name": doc.name,
		"kind": kind,
		"employee": doc.get("employee"),
		"who": doc.get("employee_name") or doc.get("employee"),
		"when": when,
		"detail": detail,
		"reason": reason,
		# Summed per person on the page ("5 days · 14h 30m"); overtime only.
		"hours": float(doc.get("claimed_hours") or 0) if doc.doctype == "OT Request" else 0,
		"modified": str(doc.get("modified") or ""),
		**_placement(doc.doctype, doc, me or _me(), {} if cache is None else cache),
	}


def _distance(metres) -> str:
	metres = float(metres or 0)
	return f"{metres / 1000:.2f} km away" if metres >= 1000 else f"{round(metres)} m away"


def _remote_checkins() -> list[dict]:
	"""Check-ins outside the work area waiting on the caller.

	The SAME fenced query the old Remote approvals page read, so folding them
	into this list changes where they show, never who sees them.
	"""
	from hrms.api.remote_checkin import list_pending_for_approver

	return list_pending_for_approver()


def yours_checkin_count() -> int:
	"""Check-ins outside the area SENT to the caller (Home counts YOURS only).

	The same fenced list the page reads, narrowed by the page's own rule, so
	Home's number is always the page's YOURS section.
	"""
	me, cache = _me(), {}
	count = sum(
		_sent_to_me("Remote Checkin Request", req, _employee_facts(req.get("employee"), cache), me)
		for req in _remote_checkins()
	)
	logger.info("[approvals_list] user=%s yours check-ins=%d", frappe.session.user, count)
	return count


def _remote_row(req, me: dict | None = None, cache: dict | None = None) -> dict:
	logger.debug("[approvals_list] remote check-in row %s", req.get("name"))
	return {
		"doctype": "Remote Checkin Request",
		"name": req.get("name"),
		"kind": "Check-in outside the area",
		"employee": req.get("employee"),
		"who": req.get("employee_name") or req.get("employee"),
		"when": _moment(req.get("checkin_time")),
		"detail": f"{'In' if req.get('log_type') == 'IN' else 'Out'} · {_distance(req.get('distance_m'))}",
		"reason": req.get("employee_remarks") or "",
		"selfie_image": req.get("selfie_image"),
		"hours": 0,
		"modified": str(req.get("checkin_time") or ""),
		**_placement("Remote Checkin Request", req, me or _me(), {} if cache is None else cache),
	}


def _day(value) -> str:
	"""'Tue 15 Sep' — the Home title's format, not an ISO date."""
	if not value:
		return ""
	d = value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
	return f"{d:%a} {d.day} {d:%b}"


def _moment(value) -> str:
	"""'Fri 18 Sep, 8:05 am' for a check-in time."""
	if not value:
		return ""
	t = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
	hour = t.hour % 12 or 12
	return f"{_day(t)}, {hour}:{t.minute:02d} {'am' if t.hour < 12 else 'pm'}"


def _range(start, end) -> str:
	start, end = _day(start), _day(end)
	return start if not end or end == start else f"{start} – {end}"


#: Candidates read per page, and the most read per type in one call. The cap
#: counts MY rows, not the site's: capping the site-wide list before asking
#: whose each row was dropped an approver's own request behind 50 older ones
#: routed elsewhere (review of 474d12d34). SCAN_LIMIT bounds the cost.
#: Offset paging over a list that can change mid-scan (a decision elsewhere)
#: may skip one row for that one load; the next load reads it. Accepted:
#: ceiling: offset paging, upgrade: keyset paging if an approver reports a
#: missing row that a reload shows.
PAGE = 100
SCAN_LIMIT = 1000


def _mine_of(
	doctype: str, field: str, pending: str, cap: int = SCAN_CAP, yours_only: bool = False
) -> tuple[list, bool]:
	"""Pending `doctype` rows routed to the caller, oldest first, up to `cap`.

	Stops as soon as it has cap + 1, so Home (cap 20) reads no more than it
	needs to say "20+". `yours_only` (Home) further keeps only what was SENT to
	the caller: it narrows what the two gates admit, never widens it.
	"""
	me, facts = (_me(), {}) if yours_only else (None, None)
	mine, start = [], 0
	while start < SCAN_LIMIT:
		names = frappe.get_all(
			doctype,
			filters={field: pending, "docstatus": 0},
			pluck="name",
			order_by="modified asc",
			limit=PAGE,
			start=start,
			ignore_permissions=True,
		)
		for name in names:
			doc = frappe.get_doc(doctype, name)
			if _request_read_allowed(doc) and _is_routed_approver(doc):
				if me and not _sent_to_me(doctype, doc, _employee_facts(doc.get("employee"), facts), me):
					continue
				mine.append(doc)
				if len(mine) > cap:
					return mine[:cap], True
		if len(names) < PAGE:
			return mine, False
		start += PAGE
	# Gave up scanning; that is not "more than the cap" (review of
	# f0cd01580: Home said "20+" while the page listed three). What was found
	# is what both show; the log says the scan was cut short.
	logger.warning("[approvals_list] %s: scanned %d pending, stopped", doctype, SCAN_LIMIT)
	return mine, False


@frappe.whitelist(methods=["GET", "POST"])
def get_waiting_for_me() -> dict:
	rows, capped = [], False
	me, cache = _me(), {}
	for doctype in _types_on_site():
		field, pending = DECIDE_THEN_SUBMIT[doctype]
		try:
			mine, hit_cap = _mine_of(doctype, field, pending)
		except Exception:
			# One unavailable type must not take the page down; logged by name
			# so a silent zero is never mistaken for an empty queue.
			logger.exception("[approvals_list] %s failed; skipped", doctype)
			continue
		capped = capped or hit_cap
		rows.extend(_row(doc, me, cache) for doc in mine)
	try:
		rows.extend(_remote_row(req, me, cache) for req in _remote_checkins())
	except Exception:
		logger.exception("[approvals_list] remote check-ins failed; skipped")
	# Oldest first: the one waiting longest is the one to decide next.
	rows.sort(key=lambda row: row["modified"])
	yours = sum(row["section"] == YOURS for row in rows)
	logger.info(
		"[approvals_list] user=%s rows=%d yours=%d capped=%s", frappe.session.user, len(rows), yours, capped
	)
	return {"rows": rows, "capped": capped}
