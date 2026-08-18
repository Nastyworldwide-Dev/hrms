"""The geofence preflight and the enforcing insert must resolve one assignment.

`hrms.utils.geofence.evaluate_geofence` has always decided correctly, and
`test_geofence.test_strict_no_shift_location_throws` has always passed. The bug
was one level up: every caller ran its OWN Shift Assignment query, and the
three copies disagreed.

  * `CustomEmployeeCheckin` filtered on `shift_location is set` — and then read
    `enable_strict_geofence` off whatever that filter returned. A strict
    assignment with no location matched nothing, `strict` defaulted to False,
    and the strict/no-location branch was unreachable from the ONLY path that
    can stop a check-in. The passing unit test was covering a branch production
    could not enter.
  * `check_geofence` did not filter on it, so the PWA refused the very punch
    the REST API accepted.

This pins the single resolver and fails if a fourth copy is written, or if the
location filter comes back.

AST only — no bench required.
"""

import ast
import pathlib
import unittest

HRMS = pathlib.Path(__file__).resolve().parent.parent

#: The geofence functions that must go through
#: `hrms.utils.geofence.resolve_assignment` rather than querying it themselves.
#: Scoped to the FUNCTION, not the file: `CustomEmployeeCheckin.fetch_shift`
#: legitimately queries Shift Assignment for a different question — which of
#: several overlapping shifts a punch belongs to — and must keep doing so.
CALLERS = {
	"api/geofence.py": ("check_geofence", "get_active_shift_location"),
	"overrides/employee_checkin_override.py": ("validate_distance_from_shift_location",),
}

_READERS = ("get_all", "get_list", "get_value", "sql", "count")


def _assignment_queries_in(func) -> list[int]:
	"""Lines inside `func` that build a Shift Assignment read."""
	hits = []
	for node in ast.walk(func):
		if not isinstance(node, ast.Call):
			continue
		if getattr(node.func, "attr", None) not in _READERS:
			continue
		for arg in node.args:
			if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
				continue
			if arg.value == "Shift Assignment" or "tabShift Assignment" in arg.value:
				hits.append(node.lineno)
	return sorted(set(hits))


def _functions(tree, names) -> dict:
	return {
		node.name: node
		for node in ast.walk(tree)
		if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name in names
	}


class TestSingleGeofenceResolver(unittest.TestCase):
	def test_resolver_does_not_filter_on_shift_location(self):
		"""The filter that hid the strict flag must never come back.

		`enable_strict_geofence` is read off the row this query selects, so
		requiring a shift_location silently downgrades every strict assignment
		that has not got one — the exact combination that must throw.
		"""
		src = (HRMS / "utils" / "geofence.py").read_text()
		start = src.index("def resolve_assignment")
		body = src[start : src.index("\ndef ", start + 1)]
		code = body.split('"""')[-1]  # drop the docstring, which discusses the filter
		self.assertNotIn(
			"shift_location",
			code,
			"resolve_assignment must not filter on shift_location — evaluate_geofence "
			"decides what a missing location means, and it can only do that if the "
			"strict flag survives the query.",
		)

	def test_geofence_functions_do_not_run_their_own_query(self):
		for rel, fnames in CALLERS.items():
			tree = ast.parse((HRMS / rel).read_text())
			found = _functions(tree, fnames)
			self.assertEqual(
				set(found),
				set(fnames),
				f"{rel}: expected geofence functions were renamed or removed",
			)
			for fname, func in found.items():
				with self.subTest(file=rel, func=fname):
					self.assertEqual(
						_assignment_queries_in(func),
						[],
						f"{rel}:{fname} builds its own Shift Assignment query. Use "
						f"hrms.utils.geofence.resolve_assignment — two queries for one "
						f"policy is how the preflight and the insert drifted apart.",
					)

	def test_callers_import_the_shared_resolver(self):
		for rel in CALLERS:
			with self.subTest(file=rel):
				src = (HRMS / rel).read_text()
				self.assertIn("resolve_assignment", src, f"{rel} should use the shared resolver")


if __name__ == "__main__":
	unittest.main()
