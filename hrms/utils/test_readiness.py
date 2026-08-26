"""Nothing here distinguished "working" from "never asked to work".

Every serious defect this system has produced was the same shape, and none of
them raised anything:

    the scheduler was off ............ check-ins never became Attendance
    a setting was off ................ the whole geofence never ran
    a counter never advanced ......... nobody could check in at all
    a config row was missing ......... no radius, so nobody was ever "inside"
    an approver resolved to None ..... requests nobody could see

Absence produces no error. A feature that is switched off, unconfigured, or
unreachable looks exactly like one that is fine — which is why these were found
by an employee failing to clock in, not by us.

`evaluate` is the answer, and it is PURE on purpose. It takes facts and returns
findings, so every rule below is tested without a bench and cannot drift from
what the collector reads. That matters here more than usual: a health check that
is itself broken is worse than none, because it actively reassures.

Deliberately opinionated about severity. `fail` means an employee's action
silently does nothing. `warn` means a real choice somebody may have made on
purpose — geolocation off is a privacy decision, not a defect, and shouting
about it would train people to ignore the whole report.

Bench-free. Run it as a FILE:

    python3 hrms/utils/test_readiness.py
"""

import ast
import pathlib
import unittest
from typing import ClassVar

SOURCE = pathlib.Path(__file__).resolve().parent / "readiness.py"


def _evaluate():
	"""`evaluate` and the constants it reads, lifted without a bench."""
	body = ast.parse(SOURCE.read_text()).body
	# Assignments only from the top level and only plain names — `logger =
	# logging.getLogger(...)` is module setup, not a constant this rule reads,
	# and lifting it drags an import that has no business in a pure test.
	wanted = [
		n
		for n in body
		if (isinstance(n, ast.FunctionDef) and n.name in ("evaluate", "_finding"))
		or (
			isinstance(n, ast.Assign)
			and isinstance(n.value, ast.Constant)
			and all(isinstance(t, ast.Name) for t in n.targets)
		)
	]
	ns = {}
	exec(compile(ast.Module(body=wanted, type_ignores=[]), str(SOURCE), "exec"), ns)
	assert "evaluate" in ns, "readiness.evaluate is missing"
	return ns["evaluate"]


#: A correctly configured site. Every test below breaks exactly one thing, so a
#: finding can only come from the fact it names.
HEALTHY = {
	"scheduler_inactive": False,
	"checkin_enabled": True,
	"geo_enabled": True,
	"auto_attendance_shifts": 3,
	"total_shifts": 3,
	"shift_locations": 2,
	"locations_without_coords": [],
	"locations_without_radius": [],
	"orphan_requests": 0,
	"series_behind": {},
}


def facts(**overrides):
	return {**HEALTHY, **overrides}


def ids(findings):
	return {f["id"] for f in findings}


def by_id(findings, key):
	return next(f for f in findings if f["id"] == key)


class TestAHealthySiteIsQuiet(unittest.TestCase):
	def test_nothing_is_reported(self):
		"""A report that always says something gets ignored within a week."""
		self.assertEqual(_evaluate()(facts()), [])


class TestTheSilentKillers(unittest.TestCase):
	"""Each of these lets an employee act and produces nothing."""

	def setUp(self):
		self.evaluate = _evaluate()

	def test_an_inactive_scheduler_fails(self):
		found = self.evaluate(facts(scheduler_inactive=True))
		self.assertIn("scheduler", ids(found))
		self.assertEqual(by_id(found, "scheduler")["status"], "fail")

	def test_no_shift_has_auto_attendance(self):
		"""The chain nobody thinks about: check-ins are raw logs until this runs.

		Staff punch in all week and the Attendance report stays empty."""
		found = self.evaluate(facts(auto_attendance_shifts=0))
		self.assertEqual(by_id(found, "auto_attendance")["status"], "fail")

	def test_some_shifts_without_auto_attendance_is_only_a_warning(self):
		"""A site can legitimately run one shift on manual attendance."""
		found = self.evaluate(facts(auto_attendance_shifts=2, total_shifts=3))
		self.assertEqual(by_id(found, "auto_attendance")["status"], "warn")

	def test_naming_counters_behind_their_rows_fails(self):
		"""The check-in blocker, as a standing check rather than a one-off patch.

		If this ever reappears — a restore from backup, a manual import — it is
		named before an employee meets it."""
		found = self.evaluate(facts(series_behind={"EMP-CKIN-08-2026-": (0, 312)}))
		self.assertEqual(by_id(found, "naming_series")["status"], "fail")

	def test_requests_with_no_approver_fail(self):
		"""resolve_approver can return None. The request is still created, and
		the pending list filters on approver, so nobody can ever see it."""
		found = self.evaluate(facts(orphan_requests=4))
		self.assertEqual(by_id(found, "orphan_requests")["status"], "fail")


class TestGeofenceConfiguration(unittest.TestCase):
	def setUp(self):
		self.evaluate = _evaluate()

	def test_geolocation_off_is_a_warning_not_a_failure(self):
		"""It is a privacy decision somebody may have made deliberately.

		Reporting a policy choice as a failure is how a report gets ignored."""
		found = self.evaluate(facts(geo_enabled=False))
		self.assertEqual(by_id(found, "geolocation")["status"], "warn")

	def test_geolocation_on_with_no_locations_fails(self):
		"""THIS is the incoherent state: range-checking is switched on and there
		is nothing to measure against, so every check-in is silently unchecked."""
		found = self.evaluate(facts(shift_locations=0))
		self.assertEqual(by_id(found, "shift_locations")["status"], "fail")

	def test_missing_locations_are_not_reported_when_geolocation_is_off(self):
		"""Nothing is broken — the feature simply is not in use. Two findings for
		one deliberate choice is noise."""
		found = self.evaluate(facts(geo_enabled=False, shift_locations=0))
		self.assertNotIn("shift_locations", ids(found))

	def test_a_location_without_coordinates_fails(self):
		found = self.evaluate(facts(locations_without_coords=["Menara Nasty"]))
		self.assertEqual(by_id(found, "location_coords")["status"], "fail")

	def test_a_zero_radius_fails(self):
		"""Radius 0 means nobody is ever inside. Under strict geofence it throws
		no_radius and blocks check-in outright."""
		found = self.evaluate(facts(locations_without_radius=["Menara Nasty"]))
		self.assertEqual(by_id(found, "location_radius")["status"], "fail")

	def test_the_offending_location_is_named(self):
		"""A count is not actionable. Somebody has to open the record."""
		found = self.evaluate(facts(locations_without_radius=["Menara Nasty", "KL Site"]))
		self.assertIn("Menara Nasty", by_id(found, "location_radius")["detail"])


class TestEveryFindingIsActionable(unittest.TestCase):
	"""The report exists to be acted on by whoever reads it at 9am.

	Findings without a stated fix are how a dashboard becomes wallpaper."""

	#: geo_enabled stays TRUE here on purpose. With it off, `evaluate` returns
	#: before the location rules — correctly, since none of them mean anything
	#: when no coordinates are collected. Setting it False and then asserting the
	#: location findings appear was this test's own bug, caught on first run.
	EVERYTHING_BROKEN: ClassVar[dict] = dict(
		scheduler_inactive=True,
		checkin_enabled=False,
		auto_attendance_shifts=0,
		shift_locations=0,
		locations_without_coords=["A"],
		locations_without_radius=["B"],
		orphan_requests=2,
		series_behind={"X-": (0, 9)},
	)

	def test_every_finding_carries_a_fix(self):
		found = _evaluate()(facts(**self.EVERYTHING_BROKEN))
		self.assertGreaterEqual(len(found), 7, f"only got {ids(found)}")
		for f in found:
			self.assertTrue(f.get("fix"), f"{f['id']} has no fix")
			self.assertIn(f["status"], ("fail", "warn"))
			self.assertTrue(f.get("detail"), f"{f['id']} has no detail")

	def test_every_id_is_distinct(self):
		"""Two findings sharing an id would silently overwrite each other in any
		dict-keyed rendering, and the report is meant to be rendered."""
		found = _evaluate()(facts(**self.EVERYTHING_BROKEN))
		self.assertEqual(len(ids(found)), len(found))

	def test_failures_sort_before_warnings(self):
		evaluate = _evaluate()
		found = evaluate(facts(scheduler_inactive=True, geo_enabled=False))
		self.assertEqual([f["status"] for f in found], ["fail", "warn"])


if __name__ == "__main__":
	unittest.main()
