"""Free Location: one flag, one description, every reader honours it.

HR marks a Shift Location as free for sales staff and anyone without a fixed
workplace. Their check-ins and check-outs record wherever they are and never
go to an approver. Pinned here, bench-free (JSON + AST), so a refactor cannot
drop the flag from one of the three readers and leave the others believing
the fence still applies:

  * the DocType JSON carries `is_free_location` (Check) with a description an
    HR user can act on;
  * `resolve_location` reads it, and the preflight, the map endpoint and the
    enforcing insert all forward it to `evaluate_geofence` as `free_location`;
  * `get_active_shift_location` returns `free_location` so the PWA can say so.

    PYTHONPATH=. python3 hrms/tests/test_free_location.py
"""

import ast
import json
import pathlib
import unittest

HRMS = pathlib.Path(__file__).resolve().parent.parent
JSON = HRMS / "hr/doctype/shift_location/shift_location.json"

#: function -> file, for every caller of evaluate_geofence
CALLERS = {
	"check_geofence": "api/geofence.py",
	"validate_distance_from_shift_location": "overrides/employee_checkin_override.py",
}


def _func(rel, name):
	tree = ast.parse((HRMS / rel).read_text())
	return next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)


class TestSchema(unittest.TestCase):
	def test_shift_location_has_the_flag_with_a_description(self):
		fields = {f["fieldname"]: f for f in json.loads(JSON.read_text())["fields"]}
		self.assertIn("is_free_location", fields)
		field = fields["is_free_location"]
		self.assertEqual(field["fieldtype"], "Check")
		desc = field.get("description", "").lower()
		for word in ("approver", "anywhere"):
			self.assertIn(word, desc, "HR must be told what ticking the box does")

	def test_modified_was_bumped_with_the_field(self):
		self.assertGreater(json.loads(JSON.read_text())["modified"], "2026-09-01")


class TestEveryReaderForwardsTheFlag(unittest.TestCase):
	def test_resolve_location_reads_the_flag(self):
		func = _func("utils/geofence.py", "resolve_location")
		consts = {n.value for n in ast.walk(func) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
		self.assertIn("is_free_location", consts)

	def test_callers_pass_free_location_to_the_decision(self):
		for name, rel in CALLERS.items():
			with self.subTest(caller=name):
				func = _func(rel, name)
				calls = [
					n
					for n in ast.walk(func)
					if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "evaluate_geofence"
				]
				self.assertTrue(calls, f"{rel}:{name} must call evaluate_geofence")
				for call in calls:
					self.assertIn(
						"free_location",
						{k.arg for k in call.keywords},
						f"{rel}:{name} calls evaluate_geofence without free_location",
					)

	def test_readiness_does_not_flag_a_free_location_as_misconfigured(self):
		src = (HRMS / "utils/readiness.py").read_text()
		self.assertIn('"is_free_location"', src, "readiness must read the flag")
		for key in ("locations_without_coords", "locations_without_radius"):
			line = next(ln for ln in src.splitlines() if key in ln and "for loc in" in ln)
			self.assertNotIn(
				"in locations ", line, f"{key} must iterate the fenced locations only, not every location"
			)

	def test_map_endpoint_returns_the_flag(self):
		func = _func("api/geofence.py", "get_active_shift_location")
		keys = {n.value for n in ast.walk(func) if isinstance(n, ast.Constant) and n.value == "free_location"}
		self.assertTrue(keys, "get_active_shift_location must return free_location for the PWA")


if __name__ == "__main__":
	unittest.main()
