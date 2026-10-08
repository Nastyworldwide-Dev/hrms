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

Owner ruling, 8 Oct 2026: the page lists only requests SENT to the caller. A
higher-up or HR can still step in from Desk or a notification (`decide` and
Home's scan are untouched); the "Other teams" rows are simply not on this page.
"""

import logging
import re
from datetime import date, datetime

import frappe

from hrms.api.approval import (
	APPROVER_FIELD,
	DECIDE_THEN_SUBMIT,
	_is_routed_approver,
	_leave_balance_now,
	_request_read_allowed,
	may_read_leave_reason,
	may_read_leave_reasons,
)
from hrms.api.now import _hhmm
from hrms.utils.identity import normalize_login, own_employees

logger = logging.getLogger(__name__)

#: Rows examined per type before the list stops (the same bound needs_you
#: uses): an HR operator is routed everything, and every candidate costs a
#: routed-approver check. Past it the page says the list is longer.
SCAN_CAP = 50

#: Rows read per type for THIS page (owner, 8 Oct 2026): bulk acts on up to 100 at once, so the
#: page has to hold 100 of a type. Home keeps its own cap (needs_you.SCAN_CAP).
#: ceiling: each leave row costs one live balance lookup, 100 per load at most,
#: upgrade: one batched balance query if the page is slow to open on a big queue.
LIST_CAP = 100

#: The types whose row says "a file is attached" (receipt, medical certificate).
ATTACHABLE = ("Leave Application", "Expense Claim")

#: The request's own first and last day, which the page's date filter reads. One-day types name
#: the same field twice; Replacement Leave names its bank month.
OWN_DATES = {
	"Leave Application": ("from_date", "to_date"),
	"Shift Request": ("from_date", "to_date"),
	"Attendance Request": ("from_date", "to_date"),
	"OT Request": ("ot_date", "ot_date"),
	"Expense Claim": ("posting_date", "posting_date"),
	"Replacement Leave Claim": ("bank_month", "bank_month"),
	"Compensatory Leave Request": ("work_from_date", "work_end_date"),
}

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


#: Where a row sits (owner-approved design, 23 Sep 2026). YOURS = sent to the
#: caller; OTHER = they receive it only because they are higher up the chain, or
#: HR. The page lists YOURS only since 8 Oct 2026; OTHER is still the placement
#: Desk and notification step-ins use. The two gates in `_mine_of` decide which
#: rows exist; placement never admits a row.
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


def _iso(value) -> str:
	"""'2026-10-14' for a date, a date-time or its text; '' when there is none."""
	return str(value)[:10] if value else ""


def _own_dates(doc) -> dict:
	"""`from_date` and `to_date` as plain ISO days, for the page's date filter."""
	first, last = OWN_DATES.get(doc.doctype, (None, None))
	return {"from_date": _iso(first and doc.get(first)), "to_date": _iso(last and doc.get(last))}


def _attached_names(doctype: str, docs) -> set:
	"""Which of these requests have a file attached: ONE query for the whole list, never one per row."""
	names = [doc.name for doc in docs]
	if not names:
		return set()
	found = set(
		frappe.get_all(
			"File",
			filters={"attached_to_doctype": doctype, "attached_to_name": ["in", names]},
			pluck="attached_to_name",
		)
	)
	logger.debug("[approvals_list] %s: %d of %d have a file", doctype, len(found), len(names))
	return found


def _current_shift(doc) -> str:
	"""The shift the employee works on the request's first day, '' when unknown. Never raises.

	The roster assignment covering that day, else the employee's default shift: the rule Home's
	shift window uses. NOT `get_employee_shift` at midnight: it counts a shift only when the asked
	time is inside its check-in window, so for a day shift it answered with the default shift
	instead of the rostered one (pinned by test_approvals_list, 8 Oct 2026).
	"""
	employee, day = doc.get("employee"), doc.get("from_date")
	if not (employee and day):
		return ""
	try:
		from hrms.utils.geofence import resolve_assignment

		found = resolve_assignment(employee, date.fromisoformat(_iso(day)))
		shift = (found and found.get("shift_type")) or frappe.db.get_value(
			"Employee", employee, "default_shift"
		)
	except Exception:
		logger.warning("[approvals_list] current shift unavailable for %s", doc.get("name"), exc_info=True)
		return ""
	return shift or ""


def _expense_currency(doc) -> str:
	"""The claim's own currency, else its company's default."""
	if currency := doc.get("currency"):
		return currency
	company = doc.get("company")
	return (frappe.get_cached_value("Company", company, "default_currency") if company else "") or ""


def _clock(value) -> str:
	"""'09:05' for a time field, '' when it is empty (midnight is a time, not an absence)."""
	return "" if value is None or value == "" else _hhmm(value)


def _row(
	doc,
	me: dict | None = None,
	cache: dict | None = None,
	may_read_reason: bool | None = None,
	attached: set | None = None,
) -> dict:
	"""What an approver needs to decide, in plain words. No raw field names.

	`may_read_reason` is a leave request's answer to "may the caller read the reason?" when the
	caller already asked for the whole list at once (`get_waiting_for_me`). None asks here, for
	this one request. `attached` is the same for "has a file": the names of this type that do,
	read once for the page; None looks up this one request.

	Beyond the common keys a row carries what its type needs to be decided without opening it
	(8 Oct 2026): time off `half_day`, `days`, `balance_after`, `attached`; expense `items`,
	`expense_types`, `currency`, `attached`; shift change `new_shift`, `current_shift`; fix a
	day `in_time`, `out_time`. Every row carries its own `from_date` and `to_date`.
	"""
	kind = KIND.get(doc.doctype, doc.doctype)
	when, detail, reason, extra = request_when(doc), "", "", {}
	if doc.doctype in ATTACHABLE:
		if attached is None:
			attached = _attached_names(doc.doctype, [doc])
		extra["attached"] = doc.name in attached
	if doc.doctype == "Leave Application":
		days = float(doc.get("total_leave_days") or 0)
		balance = _leave_balance_now(doc)
		extra.update(
			half_day=bool(doc.get("half_day")),
			days=days,
			# what is left once THIS is approved; None when there is no number to subtract from
			balance_after=None if balance is None else round(float(balance) - days, 3),
		)
		# Which half, when the request says (owner, 25 Sep 2026): the approver
		# decides knowing whether the person is out in the morning or afternoon.
		session = doc.get("half_day_session") if doc.get("half_day") else ""
		detail = f"{doc.get('leave_type')} · " + (
			f"Half day · {session}" if session else _days(doc.get("total_leave_days"))
		)
		# the approver sees it (they cannot decide without knowing why); the helper is the one
		# place that says who else may (owner ruling, 5 Oct 2026)
		if may_read_reason is None:
			may_read_reason = may_read_leave_reason(doc)
		reason = (doc.get("description") or "") if may_read_reason else ""
	elif doc.doctype == "OT Request":
		detail = _hours(doc.get("claimed_hours"))
		reason = doc.get("explanation") or ""
	elif doc.doctype == "Expense Claim":
		detail = f"{frappe.utils.fmt_money(doc.get('grand_total') or doc.get('total_claimed_amount') or 0)}"
		reason = doc.get("remark") or ""
		lines = doc.get("expenses") or []
		kinds = (line.get("expense_type") for line in lines if line.get("expense_type"))
		extra.update(
			items=len(lines),
			# each kind once, in the order the lines were claimed
			expense_types=list(dict.fromkeys(kinds)),
			currency=_expense_currency(doc),
		)
	elif doc.doctype == "Shift Request":
		detail = doc.get("shift_type") or ""
		extra.update(new_shift=detail, current_shift=_current_shift(doc))
	elif doc.doctype == "Attendance Request":
		detail = doc.get("reason") or ""
		reason = doc.get("explanation") or ""
		extra.update(in_time=_clock(doc.get("in_time")), out_time=_clock(doc.get("out_time")))
	elif doc.doctype == "Replacement Leave Claim":
		detail = _days(doc.get("claimed_days"))
		reason = doc.get("explanation") or ""
	elif doc.doctype == "Compensatory Leave Request":
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
		**_own_dates(doc),
		**extra,
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
		# the day it was made, so the date filter treats it like any one-day request
		"from_date": _iso(req.get("checkin_time")),
		"to_date": _iso(req.get("checkin_time")),
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


def request_when(doc) -> str:
	"""The days a request is about, in the Home title's words ('Tue 15 Sep' to 'Thu 17 Sep').
	One rule for every place that names a request: the approvals list and the cancel notice."""
	if doc.doctype == "OT Request":
		return _day(doc.get("ot_date"))
	if doc.doctype in ("Leave Application", "Shift Request", "Attendance Request"):
		return _range(doc.get("from_date"), doc.get("to_date"))
	if doc.doctype == "Replacement Leave Claim":
		return f"{date.fromisoformat(str(doc.bank_month)[:10]):%B %Y}" if doc.get("bank_month") else ""
	if doc.doctype == "Compensatory Leave Request":
		return _range(doc.get("work_from_date"), doc.get("work_end_date"))
	return ""


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
	"""The rows SENT to the caller, oldest first (owner, 8 Oct 2026: other teams are not listed here).

	Only `section == YOURS` rows are returned, with the key kept (the calendar filters on it). The
	two gates in `_mine_of` still decide what exists; this narrows what the page shows. Up to
	LIST_CAP rows per type, so a bulk action of 100 has all 100 on the page.
	"""
	rows, capped = [], False
	me, cache = _me(), {}
	for doctype in _types_on_site():
		field, pending = DECIDE_THEN_SUBMIT[doctype]
		try:
			mine, hit_cap = _mine_of(doctype, field, pending, cap=LIST_CAP)
			mine = [doc for doc in mine if _placement(doctype, doc, me, cache)["section"] == YOURS]
			capped = capped or hit_cap
			# one File query for the type, one reason batch for the leave list: never one per row
			attached = _attached_names(doctype, mine) if doctype in ATTACHABLE else None
			if doctype == "Leave Application":
				# the reason rule is asked once for the page's leave list, not once per row (6 Oct 2026)
				readable = may_read_leave_reasons(mine)
				built = [
					_row(doc, me, cache, may_read_reason=ok, attached=attached)
					for doc, ok in zip(mine, readable, strict=True)
				]
			else:
				built = [_row(doc, me, cache, attached=attached) for doc in mine]
		except Exception:
			# One unavailable type must not take the page down; logged by name
			# so a silent zero is never mistaken for an empty queue.
			logger.exception("[approvals_list] %s failed; skipped", doctype)
			continue
		rows.extend(built)
	try:
		rows.extend(
			row for req in _remote_checkins() if (row := _remote_row(req, me, cache))["section"] == YOURS
		)
	except Exception:
		logger.exception("[approvals_list] remote check-ins failed; skipped")
	# Oldest first: the one waiting longest is the one to decide next.
	rows.sort(key=lambda row: row["modified"])
	logger.info("[approvals_list] user=%s rows=%d capped=%s", frappe.session.user, len(rows), capped)
	return {"rows": rows, "capped": capped}
