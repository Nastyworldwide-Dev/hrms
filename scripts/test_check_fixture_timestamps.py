"""Tests for the fixture timestamp guard.

The positive case is the REAL commit that caused the outage, not a synthetic
one: a guard verified only against an example written to match it proves
nothing. The negative cases are synthetic on purpose — running this over a
commit that *looked* clean found two more real offenders, so no commit in
history is a stable "known good" control.

File mode, no bench: `python3 -m unittest discover -s scripts -p 'test_*.py'`
"""

import pathlib
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from check_fixture_timestamps import check, content_changed, is_synced, read_at

#: The Nadi rebrand. Changed parent_icon in nine desktop_icon fixtures and
#: nothing else, so none of it landed on any existing site.
REBRAND = "5854aec26"

OLD = {"label": "Leaves", "parent_icon": "Frappe HR", "modified": "2026-01-01 00:00:00"}
PATH = "hrms/desktop_icon/leaves.json"


def _has_commit(sha):
	return bool(subprocess.run(["git", "cat-file", "-t", sha], capture_output=True, text=True).stdout.strip())


def _changed_in(sha):
	out = subprocess.run(
		["git", "diff", "--name-only", f"{sha}^", sha], capture_output=True, text=True
	).stdout
	return [p for p in out.splitlines() if p]


class TestSyncedPaths(unittest.TestCase):
	def test_app_level_and_module_level_fixtures_are_covered(self):
		for path in (
			"hrms/desktop_icon/leaves.json",
			"hrms/workspace_sidebar/payroll.json",
			"hrms/hr/workspace/hr_setup/hr_setup.json",
			"hrms/hr/report/employee_leave_balance/employee_leave_balance.json",
			"hrms/hr/dashboard_chart/expense_claims/expense_claims.json",
			"hrms/payroll/notification/retention_bonus/retention_bonus.json",
		):
			self.assertTrue(is_synced(path), path)

	def test_doctype_json_is_exempt(self):
		"""import_file hash-gates DocType instead of timestamp-gating it
		(import_file.py:141, the `!= "DocType"` half), so a DocType edit
		without a bump still imports and must not be flagged."""
		self.assertFalse(is_synced("hrms/hr/doctype/ot_request/ot_request.json"))

	def test_unrelated_json_is_ignored(self):
		self.assertFalse(is_synced("design/tokens.json"))
		self.assertFalse(is_synced("frontend/package.json"))


class TestContentComparison(unittest.TestCase):
	def test_a_timestamp_bump_alone_is_not_a_content_change(self):
		self.assertFalse(content_changed(OLD, {**OLD, "modified": "2026-08-26 00:00:00"}))

	def test_any_other_field_is(self):
		self.assertTrue(content_changed(OLD, {**OLD, "parent_icon": "Nadi"}))


class TestGuard(unittest.TestCase):
	"""`check` against an in-memory 'new' file, with the old side stubbed."""

	def _run(self, new, old=OLD):
		return check([PATH], "IGNORED", load=lambda _p: new, _read_at=lambda _r, _p: old)

	def test_content_changed_and_timestamp_held_is_flagged(self):
		problems = self._run({**OLD, "parent_icon": "Nadi"})
		self.assertEqual(len(problems), 1)
		self.assertIn("did not advance", problems[0])

	def test_content_changed_and_timestamp_advanced_passes(self):
		self.assertEqual(self._run({**OLD, "parent_icon": "Nadi", "modified": "2026-08-26 00:00:00"}), [])

	def test_timestamp_advanced_alone_passes(self):
		self.assertEqual(self._run({**OLD, "modified": "2026-08-26 00:00:00"}), [])

	def test_nothing_changed_passes(self):
		self.assertEqual(self._run(dict(OLD)), [])

	def test_a_new_file_passes(self):
		"""No row exists on any site yet, so there is no gate to trip."""
		self.assertEqual(check([PATH], "IGNORED", load=lambda _p: OLD, _read_at=lambda _r, _p: None), [])


class TestAgainstTheRealCommit(unittest.TestCase):
	@unittest.skipUnless(_has_commit(REBRAND), f"{REBRAND} not in this clone")
	def test_it_catches_the_commit_that_emptied_the_nadi_icon(self):
		problems = check(_changed_in(REBRAND), f"{REBRAND}^", load=lambda p: read_at(REBRAND, p))
		self.assertEqual(len(problems), 9, "\n".join(problems))
		self.assertTrue(all("desktop_icon" in p for p in problems))


if __name__ == "__main__":
	unittest.main()
