"""Every company-overridable setting must be read through the company layer.

`hrms.utils.company_settings.COMPANY_OVERRIDES` registers the settings that a
Company may override. The whole point of registering one is that no caller
reads the global singleton directly any more — a caller that does silently
ignores the override.

That is not hypothetical. `allow_geolocation_tracking` was registered and only
the PREFLIGHT (`hrms.api.geofence.check_geofence`) was migrated; all three
paths that actually block a check-in kept reading the global, so a company that
switched geolocation on was warned in the UI and never enforced at the insert.
`email_salary_slip_to_employee` had the same split: the bulk payroll run
honoured a company's opt-out while an individually submitted slip still emailed
the slip.

Both were found by reading. This test is so the next one is found by CI.

Deliberately import-free (AST only), so it runs with or without a bench.
"""

import ast
import pathlib
import unittest

HRMS = pathlib.Path(__file__).resolve().parent.parent

#: The reader that IS the fallback, plus migrations that legitimately seed an
#: override FROM the global value they are replacing.
EXEMPT = {
	"utils/company_settings.py",
	"tests/test_company_setting_reads.py",
}
EXEMPT_DIRS = ("patches/",)


def _registered_settings() -> dict:
	"""COMPANY_OVERRIDES keys -> singleton, read straight from the source."""
	tree = ast.parse((HRMS / "utils" / "company_settings.py").read_text())
	for node in ast.walk(tree):
		if not isinstance(node, ast.Assign):
			continue
		if not any(getattr(t, "id", None) == "COMPANY_OVERRIDES" for t in node.targets):
			continue
		return {
			key.value: value.elts[0].value
			for key, value in zip(node.value.keys, node.value.values, strict=True)
			if isinstance(key, ast.Constant) and isinstance(value, ast.Tuple)
		}
	raise AssertionError("COMPANY_OVERRIDES not found in hrms/utils/company_settings.py")


def _singles_dict_reads():
	"""Yield (relpath, lineno, setting) where a registered key is read off a
	`get_singles_dict(<singleton>)` result.

	The second read path. `get_hr_settings` served the PWA the GLOBAL
	`allow_geolocation_tracking` through exactly this shape — `settings =
	get_singles_dict("HR Settings")` then `settings.allow_geolocation_tracking`
	— and CheckInPanel gates coordinate capture on that value, so a company
	that switched the override ON (global OFF) would have had no coordinates
	captured while the per-company insert path requires them: the rollout flag
	would have BLOCKED that company's check-ins. The get_single_value scan
	below cannot see this; this one can.

	Heuristic on purpose: any name assigned from get_singles_dict of a
	registered singleton taints attribute/subscript access of a registered key
	within the same function. Over-matching is acceptable — the fix (resolve
	that key through the company layer) is always valid.
	"""
	registered = _registered_settings()
	singletons = set(registered.values())
	for path in sorted(HRMS.rglob("*.py")):
		rel = path.relative_to(HRMS).as_posix()
		if rel in EXEMPT or rel.startswith(EXEMPT_DIRS) or "__pycache__" in rel:
			continue
		try:
			tree = ast.parse(path.read_text())
		except SyntaxError:  # pragma: no cover
			continue
		for func in ast.walk(tree):
			if not isinstance(func, ast.FunctionDef | ast.AsyncFunctionDef):
				continue
			tainted = set()
			for node in ast.walk(func):
				if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
					continue
				call = node.value
				if getattr(call.func, "attr", None) != "get_singles_dict" or not call.args:
					continue
				arg = call.args[0]
				if isinstance(arg, ast.Constant) and arg.value in singletons:
					tainted |= {t.id for t in node.targets if isinstance(t, ast.Name)}
			if not tainted:
				continue
			for node in ast.walk(func):
				if (
					isinstance(node, ast.Attribute)
					and isinstance(node.value, ast.Name)
					and node.value.id in tainted
					and node.attr in registered
				):
					yield rel, node.lineno, node.attr
				if (
					isinstance(node, ast.Subscript)
					and isinstance(node.value, ast.Name)
					and node.value.id in tainted
					and isinstance(node.slice, ast.Constant)
					and node.slice.value in registered
				):
					yield rel, node.lineno, node.slice.value


def _global_reads():
	"""Yield (relpath, lineno, setting) for every get_single_value of a registered key."""
	registered = _registered_settings()
	for path in sorted(HRMS.rglob("*.py")):
		rel = path.relative_to(HRMS).as_posix()
		if rel in EXEMPT or rel.startswith(EXEMPT_DIRS) or "__pycache__" in rel:
			continue
		try:
			tree = ast.parse(path.read_text())
		except SyntaxError:  # pragma: no cover
			continue
		for node in ast.walk(tree):
			if not isinstance(node, ast.Call) or len(node.args) != 2:
				continue
			if getattr(node.func, "attr", None) != "get_single_value":
				continue
			singleton, setting = node.args
			if not (isinstance(singleton, ast.Constant) and isinstance(setting, ast.Constant)):
				continue
			if registered.get(setting.value) == singleton.value:
				yield rel, node.lineno, setting.value


class TestCompanySettingReads(unittest.TestCase):
	def test_registry_is_readable(self):
		"""Guards the test itself: a refactor that moves COMPANY_OVERRIDES must not
		silently turn this into a no-op that passes by finding nothing."""
		registered = _registered_settings()
		self.assertIn("allow_geolocation_tracking", registered)
		self.assertIn("email_salary_slip_to_employee", registered)
		self.assertEqual(registered["email_salary_slip_to_employee"], "Payroll Settings")

	def test_no_singles_dict_reads_of_overridable_settings(self):
		offenders = list(_singles_dict_reads())
		self.assertEqual(
			offenders,
			[],
			"These read a company-overridable setting off a get_singles_dict() "
			"result, so the Company override is ignored on that path (the exact "
			"shape that had get_hr_settings hand the PWA the global geolocation "
			"flag). Resolve the key through hrms.utils.company_settings instead:\n"
			+ "\n".join(f"  {f}:{n} -> {s}" for f, n, s in offenders),
		)

	def test_no_direct_global_reads_of_overridable_settings(self):
		offenders = list(_global_reads())
		self.assertEqual(
			offenders,
			[],
			"These read a company-overridable setting from its global singleton, so the "
			"Company override is ignored on that path. Use "
			"hrms.utils.company_settings.get_company_setting / is_company_setting_enabled "
			"(or is_setting_enabled_for_employee where only an employee is in hand):\n"
			+ "\n".join(f"  {f}:{n} -> {s}" for f, n, s in offenders),
		)


if __name__ == "__main__":
	unittest.main()
