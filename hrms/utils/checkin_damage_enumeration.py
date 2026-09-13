"""Enumerate check-in damage — READ ONLY. Nothing here writes, ever.

WHY THIS EXISTS, AND WHY THE OBVIOUS QUERY IS WRONG
---------------------------------------------------
The first attempt at counting this damage grouped punches by calendar day and
asked for days with no OUT and two or more INs:

    ... GROUP BY employee, DATE(time) HAVING outs = 0 AND ins >= 2

It misses two whole populations, and both of them are people:

  * the ``IN, IN, OUT`` day — one real pair plus one orphan. ``outs`` is 1, so
    the day is excluded, yet the orphan is exactly the defect;
  * every night shift — the two INs straddle midnight and land in DIFFERENT
    ``DATE(time)`` groups, so neither group ever sees a pair.

``hrms/utils/attendance_day_audit.py`` is blind here too: its
``half-day-one-punch`` verdict sits behind ``len(linked) == 1``, so it fires
only on a day with exactly ONE punch, and ``punches-split-across-shifts`` needs
``has_pair >= {"IN", "OUT"}``, which two INs never satisfy. A day carrying the
reported shapes reads as ``marked`` — healthy.

So every shape below is SESSION-scoped, not day-scoped: the unit is "an IN and
whatever closed it", which is allowed to cross midnight. That is the invariant
``test_checkin_damage_enumeration.py`` pins.

USAGE
-----
    bench --site <site> execute \
        hrms.utils.checkin_damage_enumeration.report \
        --kwargs '{"from_date": "2026-09-01", "to_date": "2026-09-14"}'

Run S6 FIRST and read it before anything else: it is the PRECONDITION. While
duplicate Active assignments of different shift types still exist, repaired days
re-corrupt, so a repair planned off S2 alone buys nothing.
"""

import frappe

logger = frappe.logger("checkin_damage_enumeration", allow_site=True, file_count=10)


#: An OUT this far after its IN is still plausibly that IN's close (night shift
#: plus overtime). Beyond it the pair is a guess, so S2 — the repair candidates —
#: stops here and the rest stays in S1 for a human to read.
REPAIR_WINDOW_HOURS = 20


# Every entry: (key, one-line question, SQL). The SQL takes %(from_date)s and
# %(to_date)s and nothing else — no shape may take a company or employee filter,
# because the point is to find damage nobody has reported.
SHAPES = {
	# ---------------------------------------------------------------- S1
	# The real detector. For each non-rejected IN, look forward to that
	# employee's NEXT IN and ask whether any OUT closed the gap. Session-scoped,
	# so a night shift crossing midnight is one row, not two half-rows.
	"S1": (
		"INs with no OUT before the same employee's next IN (open sessions)",
		"""
		SELECT c.name, c.employee, c.employee_name, c.time, c.shift, c.device_id,
		       (SELECT MIN(n.time) FROM `tabEmployee Checkin` n
		         WHERE n.employee = c.employee AND n.log_type = 'IN' AND n.time > c.time
		       ) AS next_in
		  FROM `tabEmployee Checkin` c
		 WHERE c.log_type = 'IN'
		   AND c.time BETWEEN %(from_date)s AND %(to_date)s
		   AND COALESCE(c.remote_approval_status, '') <> 'Rejected'
		   AND NOT EXISTS (
		       SELECT 1 FROM `tabEmployee Checkin` o
		        WHERE o.employee = c.employee
		          AND o.log_type = 'OUT'
		          AND o.time > c.time
		          AND COALESCE(o.remote_approval_status, '') <> 'Rejected'
		          AND o.time < COALESCE((SELECT MIN(n.time) FROM `tabEmployee Checkin` n
		                                  WHERE n.employee = c.employee
		                                    AND n.log_type = 'IN'
		                                    AND n.time > c.time), '2999-12-31')
		   )
		 ORDER BY c.employee, c.time
		""",
	),
	# ---------------------------------------------------------------- S2
	# S1 narrowed to sessions whose next IN arrives soon enough that the second
	# IN is almost certainly a mislabelled OUT. THESE are the repair candidates;
	# S1 minus S2 is for a human to read, not for a script to rewrite.
	# The literal 20 below is REPAIR_WINDOW_HOURS. It is spelled out rather than
	# interpolated so the SQL stays a plain string constant that a bench-free
	# test can read straight out of the source; the test pins the two together.
	"S2": (
		"S1 where the next IN lands within 20h (repair candidates)",
		"""
		SELECT c.name, c.employee, c.employee_name, c.time, c.shift, c.device_id, n.next_in,
		       TIMESTAMPDIFF(MINUTE, c.time, n.next_in) AS gap_minutes
		  FROM `tabEmployee Checkin` c
		  JOIN (SELECT c2.name AS cname, MIN(nx.time) AS next_in
		          FROM `tabEmployee Checkin` c2
		          JOIN `tabEmployee Checkin` nx
		            ON nx.employee = c2.employee AND nx.log_type = 'IN' AND nx.time > c2.time
		         WHERE c2.log_type = 'IN'
		         GROUP BY c2.name) n ON n.cname = c.name
		 WHERE c.log_type = 'IN'
		   AND c.time BETWEEN %(from_date)s AND %(to_date)s
		   AND COALESCE(c.remote_approval_status, '') <> 'Rejected'
		   AND n.next_in <= c.time + INTERVAL 20 HOUR
		   AND NOT EXISTS (
		       SELECT 1 FROM `tabEmployee Checkin` o
		        WHERE o.employee = c.employee AND o.log_type = 'OUT'
		          AND o.time > c.time AND o.time < n.next_in
		          AND COALESCE(o.remote_approval_status, '') <> 'Rejected'
		   )
		 ORDER BY c.employee, c.time
		""",
	),
	# ---------------------------------------------------------------- S3
	"S3": (
		"two Attendance rows on one employee-day (the split-day damage)",
		"""
		SELECT employee, employee_name, attendance_date, COUNT(*) AS rows_on_day,
		       GROUP_CONCAT(name) AS attendance_rows,
		       GROUP_CONCAT(DISTINCT shift) AS shifts
		  FROM `tabAttendance`
		 WHERE docstatus < 2
		   AND attendance_date BETWEEN %(from_date)s AND %(to_date)s
		 GROUP BY employee, attendance_date
		HAVING rows_on_day > 1
		 ORDER BY employee, attendance_date
		""",
	),
	# ---------------------------------------------------------------- S4
	# The shape attendance_day_audit calls healthy: both an IN and an OUT exist,
	# so it is not "one punch", yet the day still paid nothing.
	"S4": (
		"Half Day or 0h attendance on a day holding BOTH an IN and an OUT",
		"""
		SELECT a.name, a.employee, a.employee_name, a.attendance_date, a.status,
		       a.working_hours, a.shift
		  FROM `tabAttendance` a
		 WHERE a.docstatus < 2
		   AND a.attendance_date BETWEEN %(from_date)s AND %(to_date)s
		   AND (a.status = 'Half Day' OR COALESCE(a.working_hours, 0) = 0)
		   AND EXISTS (SELECT 1 FROM `tabEmployee Checkin` i
		                WHERE i.employee = a.employee AND i.log_type = 'IN'
		                  AND DATE(i.time) = a.attendance_date)
		   AND EXISTS (SELECT 1 FROM `tabEmployee Checkin` o
		                WHERE o.employee = a.employee AND o.log_type = 'OUT'
		                  AND DATE(o.time) = a.attendance_date)
		 ORDER BY a.employee, a.attendance_date
		""",
	),
	# ---------------------------------------------------------------- S5
	# A punch with no shift makes _get_shift_ot_config return None, and
	# ot_calculation then `continue`s the slice — the employee is told they have
	# no overtime, with no reason given. Silent-zero source S1 in the OT audit.
	"S5": (
		"punches with no shift stamp (these make OT silently evaluate to 0.0h)",
		"""
		SELECT name, employee, employee_name, time, log_type, device_id
		  FROM `tabEmployee Checkin`
		 WHERE time BETWEEN %(from_date)s AND %(to_date)s
		   AND (shift IS NULL OR shift = '')
		 ORDER BY employee, time
		""",
	),
	# ---------------------------------------------------------------- S6
	# THE PRECONDITION. Two Active open-ended assignments of different shift
	# types is what lets one day resolve against two shifts. shift_rules returns
	# "skipped-manual" before closing its own auto rows, so these are still
	# being created. Read this BEFORE planning any repair.
	"S6": (
		"employees with 2+ Active open-ended assignments of DIFFERENT shift types",
		"""
		SELECT employee, employee_name, COUNT(*) AS open_assignments,
		       COUNT(DISTINCT shift_type) AS distinct_shifts,
		       GROUP_CONCAT(DISTINCT shift_type) AS shifts,
		       GROUP_CONCAT(name) AS assignment_rows
		  FROM `tabShift Assignment`
		 WHERE docstatus = 1
		   AND status = 'Active'
		   AND (end_date IS NULL OR end_date >= %(to_date)s)
		 GROUP BY employee
		HAVING distinct_shifts > 1
		 ORDER BY open_assignments DESC, employee
		""",
	),
	# ---------------------------------------------------------------- S7
	# Each untyped row in a 3-day window disables resolve_punch_type's
	# correction for that employee entirely — the guard returns before the
	# mirrored/rejected filter runs, so even a mirrored untyped row counts.
	"S7": (
		"untyped punches (each disables the punch-type correction for 3 days)",
		"""
		SELECT name, employee, employee_name, time, shift, device_id,
		       synced_from_instance
		  FROM `tabEmployee Checkin`
		 WHERE time BETWEEN %(from_date)s AND %(to_date)s
		   AND (log_type IS NULL OR log_type NOT IN ('IN', 'OUT'))
		 ORDER BY employee, time
		""",
	),
}

#: The order to read them in. S6 first: it bounds every other number.
READING_ORDER = ("S6", "S2", "S1", "S3", "S4", "S5", "S7")


def run_shape(key: str, from_date: str, to_date: str) -> list[dict]:
	"""Run one shape and return its rows. Read-only; raises on an unknown key."""
	if key not in SHAPES:
		frappe.throw(f"Unknown shape {key!r} — known shapes are {', '.join(sorted(SHAPES))}")
	question, sql = SHAPES[key]
	rows = frappe.db.sql(
		sql,
		{"from_date": f"{from_date} 00:00:00", "to_date": f"{to_date} 23:59:59"},
		as_dict=True,
	)
	logger.info("[checkin_damage] %s (%s) %s..%s -> %d rows", key, question, from_date, to_date, len(rows))
	return rows


def report(from_date: str, to_date: str, shapes: str | None = None) -> dict:
	"""Run every shape (or a comma-separated subset) and return counts + rows.

	Read-only by construction: each shape is a SELECT and nothing here writes.
	`shapes` accepts e.g. "S6,S2" to run the precondition and the repair
	candidates alone.
	"""
	keys = [k.strip().upper() for k in shapes.split(",")] if shapes else list(READING_ORDER)
	logger.info("[checkin_damage] report %s..%s shapes=%s", from_date, to_date, ",".join(keys))
	out = {}
	for key in keys:
		rows = run_shape(key, from_date, to_date)
		out[key] = {"question": SHAPES[key][0], "count": len(rows), "rows": rows}
	summary = ", ".join(f"{k}={out[k]['count']}" for k in keys)
	logger.info("[checkin_damage] report complete %s..%s: %s", from_date, to_date, summary)
	print(f"\ncheck-in damage {from_date}..{to_date}")
	for key in keys:
		print(f"  {key}  {out[key]['count']:>6}  {out[key]['question']}")
	if out.get("S6", {}).get("count"):
		print(
			"\n  S6 is NON-ZERO: duplicate Active shift assignments still exist, so repaired days\n"
			"  will re-corrupt. Close S6 before planning any repair off S2."
		)
	return out
