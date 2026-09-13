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

import logging

import frappe

logger = logging.getLogger(__name__)


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
		       c.offshift, c.skip_auto_attendance, c.remote_approval_status,
		       c.synced_from_instance, c.is_abandoned,
		       (SELECT MIN(n.time) FROM `tabEmployee Checkin` n
		         WHERE n.employee = c.employee AND n.log_type = 'IN' AND n.time > c.time
		           AND COALESCE(n.remote_approval_status, '') <> 'Rejected'
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
		                                    AND n.time > c.time
		                                    AND COALESCE(n.remote_approval_status, '') <> 'Rejected'
		                                ), '2999-12-31')
		   )
		 ORDER BY c.employee, c.time
		""",
	),
	# ---------------------------------------------------------------- S2
	# S1 narrowed to sessions whose next IN arrives soon enough that the second
	# IN is almost certainly a mislabelled OUT. THESE are the repair candidates;
	# S1 minus S2 is for a human to read, not for a script to rewrite.
	#
	# It narrows on three axes, not just the 20 hours: mirrored rows are dropped
	# because sync/write_block refuses writes to them, so a candidate that cannot
	# be repaired here is not a candidate; and already-swept rows are dropped for
	# the same reason. Still a strict subset of S1 — verified empirically, S2
	# minus S1 is the empty set.
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
		           AND COALESCE(nx.remote_approval_status, '') <> 'Rejected'
		         WHERE c2.log_type = 'IN'
		           AND c2.time BETWEEN %(from_date)s AND %(to_date)s
		         GROUP BY c2.name) n ON n.cname = c.name
		 WHERE c.log_type = 'IN'
		   AND c.time BETWEEN %(from_date)s AND %(to_date)s
		   AND COALESCE(c.remote_approval_status, '') <> 'Rejected'
		   AND COALESCE(c.synced_from_instance, '') = ''
		   AND COALESCE(c.is_abandoned, 0) = 0
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
		       GROUP_CONCAT(DISTINCT shift) AS shifts,
		       GROUP_CONCAT(DISTINCT docstatus) AS docstatuses,
		       GROUP_CONCAT(DISTINCT status) AS statuses
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
	#
	# Correlated through `Employee Checkin.attendance` — the link the marking
	# code itself writes — NOT through DATE(punch) = attendance_date. The date
	# form re-introduces exactly the blindness this module exists to remove: a
	# shift starting Monday 22:00 has its OUT at 06:00 on TUESDAY, so "is there
	# an OUT on Monday" is false and a genuinely broken night-shift row goes
	# unreported; and a continuous night worker's 06:00 OUT closing SUNDAY's
	# shift makes the same test pass by coincidence on a healthy Monday row.
	# The link answers about this row's own punches and nothing else.
	"S4": (
		"Half Day or 0h attendance whose OWN linked punches hold both an IN and an OUT",
		"""
		SELECT a.name, a.employee, a.employee_name, a.attendance_date, a.status,
		       a.working_hours, a.shift, a.docstatus, a.in_time, a.out_time
		  FROM `tabAttendance` a
		 WHERE a.docstatus < 2
		   AND a.attendance_date BETWEEN %(from_date)s AND %(to_date)s
		   AND (a.status = 'Half Day' OR COALESCE(a.working_hours, 0) = 0)
		   AND EXISTS (SELECT 1 FROM `tabEmployee Checkin` i
		                WHERE i.attendance = a.name AND i.log_type = 'IN')
		   AND EXISTS (SELECT 1 FROM `tabEmployee Checkin` o
		                WHERE o.attendance = a.name AND o.log_type = 'OUT')
		 ORDER BY a.employee, a.attendance_date
		""",
	),
	# ---------------------------------------------------------------- S5
	# A punch with no shift makes _get_shift_ot_config return None, and
	# ot_calculation then `continue`s the slice — the employee is told they have
	# no overtime, with no reason given. Silent-zero source S1 in the OT audit.
	#
	# `offshift = 0` is not optional here. employee_checkin sets shift = None and
	# offshift = 1 together when no window matches, and OT ignores off-shift
	# punches BY DESIGN — so without this the count is dominated by punches that
	# are behaving correctly, burying the population that is actually damaged:
	# a punch that should have a shift and does not.
	"S5": (
		"punches with no shift stamp (these make OT silently evaluate to 0.0h)",
		"""
		SELECT name, employee, employee_name, time, log_type, device_id, offshift
		  FROM `tabEmployee Checkin`
		 WHERE time BETWEEN %(from_date)s AND %(to_date)s
		   AND (shift IS NULL OR shift = '')
		   AND COALESCE(offshift, 0) = 0
		 ORDER BY employee, time
		""",
	),
	# ---------------------------------------------------------------- S6
	# THE PRECONDITION. Two Active assignments of different shift types covering
	# one day is what lets that day resolve against two shifts.
	#
	# The source in shift_rules is CLOSED as of b2ab6ce0f — the manual-wins
	# branch now closes its own rows, and a row starting today is retired as
	# Inactive because end-dating cannot close it. So a non-zero count here is
	# now HISTORICAL rather than growing, and it should stop rising once that
	# is deployed. It is still the number to read first: while these pairs
	# exist, a repaired day can re-corrupt.
	"S6": (
		"employees with 2+ Active assignments of DIFFERENT shift types covering the window",
		"""
		SELECT employee, employee_name, COUNT(*) AS assignments_covering,
		       COUNT(DISTINCT shift_type) AS distinct_shifts,
		       GROUP_CONCAT(DISTINCT shift_type) AS shifts,
		       GROUP_CONCAT(name) AS assignment_rows
		  FROM `tabShift Assignment`
		 WHERE docstatus = 1
		   AND status = 'Active'
		   AND start_date <= DATE(%(to_date)s)
		   AND (end_date IS NULL OR end_date >= DATE(%(to_date)s))
		 GROUP BY employee
		HAVING distinct_shifts > 1
		 ORDER BY assignments_covering DESC, employee
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
	# ---------------------------------------------------------------- S8
	# THE DENOMINATOR FOR S4, AND IT IS NOT OPTIONAL.
	#
	# S4 asks about an attendance row's OWN linked punches, which is precise.
	# But the link is written by exactly one path (update_attendance_in_checkins),
	# and the paths that do NOT write it include HR's bulk Employee Attendance
	# Tool, mark_attendance(), Attendance Request — and, worst of all,
	# mark_attendance_and_link_log DELIBERATELY leaves punches unlinked when it
	# hits DuplicateAttendanceError or OverlappingShiftAttendanceError, which is
	# precisely the contested, damaged day S4 exists to find.
	#
	# So a small S4 is meaningless on its own: it may mean the damage is small,
	# or it may mean the link could not answer. This counts the rows the link
	# cannot answer for, and the report prints the two together so a clean-looking
	# zero can never be read as "this shape is fine".
	#
	# IT IS THE EXACT COMPLEMENT OF S4, DELIBERATELY. The first version asked for
	# rows with NO linked punch at all, which is NOT the negation of "has a linked
	# IN and a linked OUT": a row with ONE linked punch satisfied neither, so it
	# fell out of both buckets and the caveat never fired for it. That state is
	# reachable — attendance_day_audit unlinks punches one name at a time, and
	# this repo's own audit already has a verdict for a Half Day with a single
	# linked punch. S4 and S8 now partition the Half-Day/0h population exactly.
	"S8": (
		"Half Day or 0h attendance S4 could NOT confirm (no linked IN/OUT pair)",
		"""
		SELECT a.name, a.employee, a.employee_name, a.attendance_date, a.status,
		       a.working_hours, a.shift, a.docstatus
		  FROM `tabAttendance` a
		 WHERE a.docstatus < 2
		   AND a.attendance_date BETWEEN %(from_date)s AND %(to_date)s
		   AND (a.status = 'Half Day' OR COALESCE(a.working_hours, 0) = 0)
		   AND NOT (EXISTS (SELECT 1 FROM `tabEmployee Checkin` i
		                     WHERE i.attendance = a.name AND i.log_type = 'IN')
		            AND EXISTS (SELECT 1 FROM `tabEmployee Checkin` o
		                         WHERE o.attendance = a.name AND o.log_type = 'OUT'))
		 ORDER BY a.employee, a.attendance_date
		""",
	),
	# ---------------------------------------------------------------- S9
	# The bucket S5 excludes, counted rather than dropped.
	#
	# A punch gets offshift = 1 for two very different reasons: it genuinely fell
	# outside every shift window (by design, and OT ignores it by design), OR no
	# assignment matched at all — a lapsed or duplicated assignment, which is
	# damage and is exactly the S6 condition. Both still evaluate to 0.0h of
	# overtime. S5 keeps the anomalous population clean; this keeps the other one
	# visible instead of silently gone.
	"S9": (
		"punches stamped off-shift (by design, OR no assignment matched — both yield 0.0h OT)",
		"""
		SELECT name, employee, employee_name, time, log_type, shift, device_id
		  FROM `tabEmployee Checkin`
		 WHERE time BETWEEN %(from_date)s AND %(to_date)s
		   AND COALESCE(offshift, 0) = 1
		 ORDER BY employee, time
		""",
	),
}


#: A shape that can only answer for PART of its population, and the shape that
#: counts the rest. Neither number means anything alone, so `report` refuses to
#: run one without the other.
DENOMINATORS = {"S4": "S8", "S5": "S9"}

#: The order to read them in. S6 first: it bounds every other number. S8 sits
#: directly under S4 and S9 under S5, because each is the other's denominator —
#: read alone, either of those two can show a reassuring zero it has not earned.
READING_ORDER = ("S6", "S2", "S1", "S3", "S4", "S8", "S5", "S9", "S7")


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


#: How many matched rows `report` hands back per shape by default. `bench
#: execute` prints whatever it is returned, and on production a shape can match
#: tens of thousands of rows — enough to bury the counts that are the point of
#: running it. Pass `sample=0` for everything.
DEFAULT_SAMPLE = 25


def report(from_date: str, to_date: str, shapes: str | None = None, sample: int = DEFAULT_SAMPLE) -> dict:
	"""Run every shape (or a comma-separated subset) and return counts + rows.

	Read-only by construction: each shape is a SELECT and nothing here writes.
	`shapes` accepts e.g. "S6,S2" to run the precondition and the repair
	candidates alone. `sample` caps the rows returned per shape — the COUNTS are
	always complete and always computed from every matching row; only the
	returned sample is trimmed. `sample=0` returns everything.
	"""
	keys = [k.strip().upper() for k in shapes.split(",")] if shapes else list(READING_ORDER)
	# A shape whose evidence is sometimes missing cannot be read alone, so asking
	# for one drags its denominator along. Without this, `shapes="S4"` printed a
	# bare zero with no caveat — the exact reading this pairing exists to forbid.
	for shape, denominator in DENOMINATORS.items():
		if shape in keys and denominator not in keys:
			keys.insert(keys.index(shape) + 1, denominator)
			logger.info("[checkin_damage] %s cannot be read alone — adding %s", shape, denominator)
	logger.info(
		"[checkin_damage] report %s..%s shapes=%s sample=%s", from_date, to_date, ",".join(keys), sample
	)
	out = {}
	for key in keys:
		rows = run_shape(key, from_date, to_date)
		out[key] = {"question": SHAPES[key][0], "count": len(rows), "rows": rows}
	# Rows, then PEOPLE. One employee with five orphan INs is five rows and one
	# person, and every decision taken off this report is about people.
	for key in keys:
		rows = out[key]["rows"]
		out[key]["employees"] = len({r.get("employee") for r in rows if r.get("employee")})
		if sample and len(rows) > sample:
			out[key]["rows"] = rows[:sample]
			out[key]["truncated"] = True
	summary = ", ".join(f"{k}={out[k]['count']}r/{out[k]['employees']}p" for k in keys)
	logger.info("[checkin_damage] report complete %s..%s: %s", from_date, to_date, summary)
	print(f"\ncheck-in damage {from_date}..{to_date}    (rows / distinct employees)")
	for key in keys:
		print(f"  {key}  {out[key]['count']:>7} / {out[key]['employees']:>5}  {out[key]['question']}")
	truncated = [k for k in keys if out[k].get("truncated")]
	if truncated:
		print(f"\n  rows trimmed to {sample} for {', '.join(truncated)} — counts above are complete")
	for shape, denominator in DENOMINATORS.items():
		if out.get(denominator, {}).get("count") and shape in out:
			print(
				f"\n  {shape} could not answer for {out[denominator]['count']} row(s) of its own\n"
				f"  population — see {denominator}. Do not read {shape} as complete while\n"
				f"  {denominator} is non-zero."
			)
	if out.get("S6", {}).get("count"):
		print(
			"\n  S6 is NON-ZERO: duplicate Active shift assignments still exist, so repaired days\n"
			"  will re-corrupt. Close S6 before planning any repair off S2."
		)
	return out
