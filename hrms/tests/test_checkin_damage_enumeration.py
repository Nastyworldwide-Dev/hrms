"""The enumeration must stay SESSION-scoped, not day-scoped.

This is the invariant that the first attempt got wrong: grouping punches by
``DATE(time)`` silently drops the ``IN, IN, OUT`` day and every night shift,
because a night shift's two INs land either side of midnight and therefore in
different groups. A day-grouped query cannot see either population, so it
reports a comfortable number that is an undercount.

Bench-free on purpose: it reads the module's SQL as text. `bench run-tests` is
dead in this tree, and this check must survive that.
"""

import ast
import re
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "utils" / "checkin_damage_enumeration.py"

#: Shapes S3 and S6 are legitimately grouped — S3 asks "how many Attendance rows
#: exist on one employee-day", which IS a day question, and S6 groups by employee
#: with no date component at all. Every OTHER shape walks punches and must not.
DAY_GROUPED_BY_DESIGN = {"S3", "S6"}

#: S3 groups Attendance rows by their own attendance_date, and S6 groups Shift
#: Assignments by employee with no date component. Neither walks punches, so
#: neither can be blind to a midnight crossing. Every other shape must answer
#: about a SESSION, and the two ways to get that wrong are grouping punches by
#: DATE() and matching two punches by DATE() in a WHERE clause. Both are refused
#: below; S4 correlates through Employee Checkin.attendance instead, which is the
#: link the marking code writes and carries no date arithmetic at all.


def _module():
	return ast.parse(SOURCE.read_text())


def _shape_pairs() -> dict[str, tuple[str, str]]:
	"""The SHAPES dict as {key: (question, sql)}, read from the committed source."""
	for node in ast.walk(_module()):
		if isinstance(node, ast.Assign) and any(
			isinstance(t, ast.Name) and t.id == "SHAPES" for t in node.targets
		):
			return {
				ast.literal_eval(key): (
					ast.literal_eval(value.elts[0]),
					ast.literal_eval(value.elts[1]),
				)
				for key, value in zip(node.value.keys, node.value.values, strict=True)
			}
	raise AssertionError("SHAPES not found in checkin_damage_enumeration.py")


def _shapes() -> dict[str, str]:
	return {key: sql for key, (_question, sql) in _shape_pairs().items()}


def _questions() -> dict[str, str]:
	return {key: question for key, (question, _sql) in _shape_pairs().items()}


class TestCheckinDamageEnumeration(unittest.TestCase):
	def test_punch_walking_shapes_never_group_by_calendar_day(self):
		"""The exact defect of the query this replaces."""
		for key, sql in _shapes().items():
			if key in DAY_GROUPED_BY_DESIGN:
				continue
			with self.subTest(shape=key):
				self.assertNotRegex(
					sql,
					r"GROUP\s+BY[^;]*DATE\s*\(",
					f"{key} groups punches by calendar day. A night shift's two INs straddle "
					f"midnight into different groups, so this cannot see the shape it exists "
					f"to find. Compare the session forward-look in S1.",
				)

	def test_no_punch_walking_shape_matches_two_punches_by_calendar_date(self):
		"""The second spelling of the same defect, and the one the first
		assertion could not see.

		`GROUP BY ... DATE(time)` is the form the replaced query used, but
		`WHERE DATE(a.time) = DATE(b.time)` is day-scoped in exactly the same
		way and reads as innocuous. A night shift's IN and its OUT land on
		different calendar dates, so any correlation written that way silently
		drops every night shift — the population this module exists to find."""
		for key, sql in _shapes().items():
			if key in DAY_GROUPED_BY_DESIGN:
				continue
			with self.subTest(shape=key):
				self.assertNotRegex(
					sql,
					r"DATE\s*\(\s*\w+\.time\s*\)",
					f"{key} matches punches by calendar date. A night shift's IN and OUT sit on "
					f"different dates, so this cannot see the shape it exists to find. Correlate "
					f"through Employee Checkin.attendance, or by the session, as S1 and S4 do.",
				)

	def test_the_open_session_detector_looks_forward_to_the_next_IN(self):
		"""S1's unit is a session, so its bound is the next IN — not midnight."""
		sql = _shapes()["S1"]
		self.assertIn("log_type = 'IN'", sql)
		self.assertRegex(sql, r"n\.time\s*>\s*c\.time", "S1 must bound the gap by the NEXT IN")
		self.assertIn("NOT EXISTS", sql, "S1 must assert that no OUT closed the gap")

	def test_rejected_punches_never_close_a_session(self):
		"""A rejected late-OUT never closed anything — the same rule the banner,
		the sweeper and the OT pairing engine already apply."""
		for key in ("S1", "S2"):
			with self.subTest(shape=key):
				self.assertIn("'Rejected'", _shapes()[key])

	def test_every_shape_is_a_read(self):
		"""Nothing in this module may write. It runs against production."""
		forbidden = re.compile(r"\b(INSERT|UPDATE|DELETE|ALTER|DROP|TRUNCATE|REPLACE)\b", re.I)
		for key, sql in _shapes().items():
			with self.subTest(shape=key):
				self.assertIsNone(forbidden.search(sql), f"{key} is not a pure read")

	def test_no_shape_takes_a_company_or_employee_filter(self):
		"""The point is to find damage nobody has reported, so a shape must not
		be narrowable to the population somebody already suspects."""
		for key, sql in _shapes().items():
			with self.subTest(shape=key):
				params = set(re.findall(r"%\((\w+)\)s", sql))
				self.assertLessEqual(
					params,
					{"from_date", "to_date"},
					f"{key} accepts {params - {'from_date', 'to_date'}} — it must scan everyone",
				)

	def test_S2_window_matches_the_declared_constant(self):
		"""S2 spells the window out in SQL so the shape stays a plain literal.
		That is only safe while the two cannot drift apart."""
		hours = None
		for node in ast.walk(_module()):
			if isinstance(node, ast.Assign) and any(
				isinstance(t, ast.Name) and t.id == "REPAIR_WINDOW_HOURS" for t in node.targets
			):
				hours = ast.literal_eval(node.value)
		self.assertIsNotNone(hours, "REPAIR_WINDOW_HOURS not found")
		self.assertIn(f"INTERVAL {hours} HOUR", _shapes()["S2"])
		self.assertIn(f"within {hours}h", _questions()["S2"])

	def test_the_precondition_is_read_first(self):
		"""S6 bounds every other number: while duplicate Active assignments
		exist, repaired days re-corrupt."""
		for node in ast.walk(_module()):
			if isinstance(node, ast.Assign) and any(
				isinstance(t, ast.Name) and t.id == "READING_ORDER" for t in node.targets
			):
				self.assertEqual(ast.literal_eval(node.value)[0], "S6")
				return
		raise AssertionError("READING_ORDER not found")

	def test_every_shape_is_in_the_reading_order(self):
		for node in ast.walk(_module()):
			if isinstance(node, ast.Assign) and any(
				isinstance(t, ast.Name) and t.id == "READING_ORDER" for t in node.targets
			):
				self.assertEqual(set(ast.literal_eval(node.value)), set(_shapes()))
				return
		raise AssertionError("READING_ORDER not found")


if __name__ == "__main__":
	unittest.main()
