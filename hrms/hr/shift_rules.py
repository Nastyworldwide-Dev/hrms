"""Location/department-driven Shift Assignment rule layer.

Shift Location holds `shift_rules` rows (department -> shift type). An
employee's shift is resolved from their `shift_location` + `department`:
a rule row matches when its department is an ancestor-or-self of the
employee's department in the Department tree (nested set), the deepest
match wins, and a row with a blank department is the site default.

The daily `sync_shift_assignments` job (and the Employee on_update hook)
materialize the resolution as ONE open-ended submitted Shift Assignment
per employee, tagged `created_by_shift_rule=1`. Manual assignments always
take precedence: if any manual assignment covers today or the future, the
employee is skipped entirely.
"""

import logging

import frappe
from frappe.utils import add_days, getdate, nowdate

logger = logging.getLogger(__name__)

# A hand-rostered (variable-shift) employee's roster segments have definite end
# dates and gaps between them. The rule layer must stand down for them, but the
# "manual wins" check only sees assignments covering today or the future, so a
# segment that ended yesterday read as "unmanaged" and the layer imposed an
# open-ended site-default shift into the gap — the "system changed a rostered
# employee to the night shift mid-month, until end of month" defect. A non-rule assignment that
# ended within one roster cycle still marks the employee roster-managed.
# ponytail: 31-day lookback ~= one roster cycle; replace with a declared
# "variable shift" employee flag when the rostering feature (Phase 1) lands.
MANUAL_ROSTER_LOOKBACK_DAYS = 31


def resolve_shift_for_employee(employee: str):
	"""Returns frappe._dict(shift_type=..., shift_location=...) or None."""
	emp = frappe.db.get_value("Employee", employee, ["shift_location", "department"], as_dict=True)
	if not emp or not emp.shift_location:
		return None

	rules = frappe.get_all(
		"Shift Location Rule",
		filters={"parenttype": "Shift Location", "parent": emp.shift_location},
		fields=["department", "shift_type"],
	)
	if not rules:
		return None

	match = None
	if emp.department:
		bounds = frappe.db.get_value("Department", emp.department, ["lft", "rgt"], as_dict=True)
		best_lft = -1
		for rule in rules:
			if not rule.department:
				continue
			rule_bounds = frappe.db.get_value("Department", rule.department, ["lft", "rgt"], as_dict=True)
			if not (bounds and rule_bounds):
				continue
			is_ancestor_or_self = rule_bounds.lft <= bounds.lft and rule_bounds.rgt >= bounds.rgt
			# deeper nodes have a larger lft, so the deepest ancestor wins
			if is_ancestor_or_self and rule_bounds.lft > best_lft:
				best_lft = rule_bounds.lft
				match = rule

	if not match:
		match = next((rule for rule in rules if not rule.department), None)

	if not match:
		return None

	return frappe._dict(shift_type=match.shift_type, shift_location=emp.shift_location)


def reconcile_employee_shift(employee: str) -> str:
	"""Reconciles one employee against the shift rules.

	Returns the action taken: created | swapped | closed | noop |
	skipped-manual | skipped-schedule | skipped-no-rule.
	"""
	today = nowdate()
	desired = resolve_shift_for_employee(employee)

	current = frappe.get_all(
		"Shift Assignment",
		filters={"employee": employee, "docstatus": 1, "status": "Active"},
		or_filters=[["end_date", "is", "not set"], ["end_date", ">=", today]],
		fields=[
			"name",
			"shift_type",
			"shift_location",
			"start_date",
			"end_date",
			"created_by_shift_rule",
		],
	)
	auto_rows = [row for row in current if row.created_by_shift_rule]

	# Explicit declaration wins over every heuristic below: a roster_managed
	# (variable-shift) employee is owned by the roster, so the rule layer hands
	# off and closes anything it created before the flag was set. This is the
	# durable replacement for the lapsed-roster lookback further down.
	if frappe.db.get_value("Employee", employee, "roster_managed"):
		for row in auto_rows:
			_close_assignment(row, today)
		logger.info("[shift_rules] %s: roster_managed — skipped (roster owns shifts)", employee)
		return "skipped-roster"

	# Mutual exclusion with the Shift Schedule machinery: an enabled Shift
	# Schedule Assignment means process_auto_shift_creation owns this
	# employee's shifts. An open-ended auto row would make every dated
	# schedule insert fail overlap validation (silently — that job swallows
	# errors), so the rule layer stands down and closes its own rows.
	if frappe.db.exists("Shift Schedule Assignment", {"employee": employee, "enabled": 1}):
		for row in auto_rows:
			_close_assignment(row, today)
		logger.info(
			"[shift_rules] %s: enabled Shift Schedule Assignment exists — skipped (schedule wins)",
			employee,
		)
		return "skipped-schedule"

	if any(not row.created_by_shift_rule for row in current) or _recent_manual_roster(employee, today):
		logger.info("[shift_rules] %s: manual assignment exists — skipped (manual wins)", employee)
		return "skipped-manual"
	matching = next(
		(
			row
			for row in auto_rows
			if desired
			and not row.end_date
			and row.shift_type == desired.shift_type
			and row.shift_location == desired.shift_location
		),
		None,
	)

	new_start = getdate(today)
	for stale in auto_rows:
		if stale is matching:
			continue
		closed_until = _close_assignment(stale, today)
		if closed_until >= new_start:
			new_start = add_days(closed_until, 1)

	if not desired:
		if auto_rows:
			logger.info("[shift_rules] %s: no rule resolves — closed auto assignment", employee)
			return "closed"
		return "skipped-no-rule"

	if matching:
		return "noop"

	_create_assignment(employee, desired, new_start)
	action = "swapped" if auto_rows else "created"
	logger.info(
		"[shift_rules] %s: %s -> %s @ %s starting %s",
		employee,
		action,
		desired.shift_type,
		desired.shift_location,
		new_start,
	)
	return action


def sync_shift_assignments():
	"""Daily scheduler job: reconcile every active employee with a shift location."""
	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active", "shift_location": ["is", "set"]},
		pluck="name",
	)

	counters = {}
	for index, employee in enumerate(employees, start=1):
		# savepoint per employee: one bad record must not poison the
		# transaction for everyone after it
		frappe.db.savepoint("shift_rule_employee")
		try:
			action = reconcile_employee_shift(employee)
		except Exception:
			frappe.db.rollback(save_point="shift_rule_employee")
			action = "error"
			logger.exception("[shift_rules] reconcile failed for %s", employee)
			frappe.log_error(
				title=f"Shift rule sync failed for {employee}",
				message=frappe.get_traceback(),
			)
		if index % 50 == 0 and not frappe.flags.in_test:
			frappe.db.commit()  # nosemgrep: keep progress on long employee lists
		counters[action] = counters.get(action, 0) + 1

	logger.info("[shift_rules] sync done — %d employees: %s", len(employees), counters)
	return counters


def reconcile_on_employee_update(doc, method=None):
	"""Employee on_update hook: reconcile immediately when the fields that
	drive the shift rules change. Never blocks the Employee save."""
	if doc.status != "Active":
		return
	if not (doc.has_value_changed("shift_location") or doc.has_value_changed("department")):
		return

	try:
		action = reconcile_employee_shift(doc.name)
		logger.info("[shift_rules] on_update reconcile %s: %s", doc.name, action)
	except Exception:
		logger.exception("[shift_rules] on_update reconcile failed for %s", doc.name)
		frappe.log_error(
			title=f"Shift rule reconcile failed for {doc.name}",
			message=frappe.get_traceback(),
		)


def _recent_manual_roster(employee: str, today: str) -> bool:
	"""True if the employee has a non-rule Shift Assignment that ended within the
	recent roster window — evidence they are hand-rostered even though no segment
	covers today. Guards a lapsed roster gap from rule takeover (Norain)."""
	return bool(
		frappe.db.exists(
			"Shift Assignment",
			{
				"employee": employee,
				"docstatus": 1,
				"created_by_shift_rule": 0,
				"end_date": ["between", [add_days(getdate(today), -MANUAL_ROSTER_LOOKBACK_DAYS), today]],
			},
		)
	)


def _close_assignment(row, today):
	"""End-dates a rule-managed assignment; never before its start date.
	Returns the end date used."""
	end_date = max(getdate(row.start_date), add_days(getdate(today), -1))
	assignment = frappe.get_doc("Shift Assignment", row.name)
	assignment.flags.ignore_permissions = True
	assignment.end_date = end_date
	assignment.save()
	logger.info("[shift_rules] closed %s (%s) at %s", row.name, row.shift_type, end_date)
	return end_date


def _create_assignment(employee: str, desired, start_date):
	company = frappe.db.get_value("Employee", employee, "company")
	assignment = frappe.get_doc(
		{
			"doctype": "Shift Assignment",
			"employee": employee,
			"company": company,
			"shift_type": desired.shift_type,
			"shift_location": desired.shift_location,
			"start_date": start_date,
			"status": "Active",
			"created_by_shift_rule": 1,
		}
	)
	assignment.flags.ignore_permissions = True
	assignment.insert()
	assignment.submit()
	return assignment
