"""The verdict this diagnostic prints decides whether someone presses Purge.

`diagnose.main` is mostly `print`, and one branch in it is not: the verdict.
That branch is the difference between "nothing to untangle" and "DO NOT PURGE",
and Purge is irreversible — it already cost one real record on this system,
deleting live rows because they happened to carry a dev stamp.

So the decision is pure and tested, the way `plan_mirror_write` and
`plan_cross_instance_write` already are here, and `main` only formats it.

The cases that matter are the ones where the two obvious signals disagree.
Registered instances and stamps found on rows are different populations — an
instance can be registered and have synced nothing, and a stamp can outlive the
instance record that produced it. Reading only one of them gets the verdict
wrong in exactly the situation the script exists for.

Bench-free: nothing here imports frappe. Run it as a FILE:

    python3 hrms/sync/test_diagnose.py
"""

import ast
import pathlib
import unittest
from typing import ClassVar

SOURCE = pathlib.Path(__file__).resolve().parent / "diagnose.py"


def _assess():
	"""`assess`, lifted out of diagnose.py without a bench.

	The function is pure; the module imports frappe at the top. Compiling just
	this definition keeps the test bench-free without the decision having to live
	away from the code that prints it.
	"""
	fn = next(
		(
			n
			for n in ast.parse(SOURCE.read_text()).body
			if isinstance(n, ast.FunctionDef) and n.name == "assess"
		),
		None,
	)
	assert fn is not None, "diagnose.assess is missing"
	ns = {}
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SOURCE), "exec"), ns)
	return ns["assess"]


def inst(name, enabled=1, unlocked=0):
	return {"name": name, "enabled": enabled, "unlock_mirrored_writes": unlocked}


class TestTheVerdict(unittest.TestCase):
	def setUp(self):
		self.assess = _assess()

	def test_one_registered_instance_with_its_own_rows_is_clean(self):
		got = self.assess([inst("Nasty-Live")], {"Nasty-Live": 312})
		self.assertEqual(got["verdict"], "one-source")

	def test_a_fresh_hub_that_has_synced_nothing_is_clean(self):
		self.assertEqual(self.assess([inst("Nasty-Live")], {})["verdict"], "one-source")

	def test_two_stamps_on_the_rows_is_the_dangerous_case(self):
		got = self.assess([inst("Nasty-Live")], {"Nasty-Live": 312, "Nasty-Dev": 40})
		self.assertEqual(got["verdict"], "multi-source")

	def test_a_disabled_clone_that_already_stamped_rows_still_warns(self):
		"""Disabling an instance stops the next pull. It un-stamps nothing.

		This is the state the system was actually left in — dev disabled, its
		stamps still spread across live rows — and it is precisely when somebody
		reaches for Purge."""
		got = self.assess(
			[inst("Nasty-Live"), inst("Nasty-Dev", enabled=0)],
			{"Nasty-Live": 312, "Nasty-Dev": 40},
		)
		self.assertEqual(got["verdict"], "multi-source")

	def test_two_enabled_instances_warn_before_either_has_synced(self):
		"""Nothing has collided yet, and the next pull is when it will.

		A verdict driven by stamps alone would call this clean and only speak up
		after the damage."""
		got = self.assess([inst("Nasty-Live"), inst("Nasty-Dev")], {})
		self.assertEqual(got["verdict"], "multi-source")


class TestOrphanStamps(unittest.TestCase):
	"""A stamp naming an instance nobody registered is unreachable both ways:
	no sync will refresh those rows and Purge cannot target them."""

	def setUp(self):
		self.assess = _assess()

	def test_a_stamp_with_no_instance_record_is_named(self):
		got = self.assess([inst("Nasty-Live")], {"Nasty-Live": 312, "Retired-ERP": 7})
		self.assertEqual(got["orphan_stamps"], ["Retired-ERP"])

	def test_a_registered_instance_is_not_an_orphan(self):
		got = self.assess([inst("Nasty-Live")], {"Nasty-Live": 312})
		self.assertEqual(got["orphan_stamps"], [])

	def test_orphans_are_sorted_so_two_runs_compare(self):
		got = self.assess([], {"z-src": 1, "a-src": 1})
		self.assertEqual(got["orphan_stamps"], ["a-src", "z-src"])


class TestUnlockIsSurfaced(unittest.TestCase):
	def setUp(self):
		self.assess = _assess()

	def test_an_unlocked_instance_is_named(self):
		got = self.assess([inst("Nasty-Live", unlocked=1)], {"Nasty-Live": 312})
		self.assertEqual(got["unlocked"], ["Nasty-Live"])

	def test_unlock_is_reported_even_on_an_otherwise_clean_hub(self):
		"""It is not a divergence, so it must not be folded into the verdict —
		and it is the single most destructive switch on the form, so it must not
		be silent either."""
		got = self.assess([inst("Nasty-Live", unlocked=1)], {"Nasty-Live": 312})
		self.assertEqual(got["verdict"], "one-source")
		self.assertEqual(got["unlocked"], ["Nasty-Live"])


class TestItIsReadOnly(unittest.TestCase):
	"""The one property that makes this safe to hand someone mid-incident.

	Read from the AST rather than by grepping for the words: the module
	docstring promises read-only in prose, and a text search would match that
	promise instead of checking it.
	"""

	FORBIDDEN: ClassVar[set[str]] = {
		"delete_doc",
		"set_value",
		"insert",
		"save",
		"submit",
		"rename_doc",
		"commit",
	}

	def test_it_calls_nothing_that_writes(self):
		tree = ast.parse(SOURCE.read_text())
		called = {
			n.func.attr
			for n in ast.walk(tree)
			if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		}
		self.assertEqual(called & self.FORBIDDEN, set(), "diagnose.py must never write")

	def test_its_sql_only_selects(self):
		tree = ast.parse(SOURCE.read_text())
		for node in ast.walk(tree):
			if isinstance(node, ast.Constant) and isinstance(node.value, str):
				text = node.value.upper()
				if "FROM `TAB" in text:
					self.assertIn("SELECT", text)
					for word in ("DELETE", "UPDATE", "INSERT", "DROP", "TRUNCATE"):
						self.assertNotIn(word, text, f"{word} in a diagnostic query")


class TestTheDeskButtonReachesIt(unittest.TestCase):
	"""The form calls this by NAME, in a string. Nothing checks that string.

	A whitelisted endpoint and the button that calls it are edited in different
	files, in different languages, and the only thing binding them is a dotted
	path typed into JS. Rename or move the function and the button keeps
	rendering, keeps freezing the screen, and fails at the network — visible only
	to whoever opens the browser console.

	That matters more than usual here: this button exists to be pressed BEFORE
	Purge, by an operator deciding whether their data is safe. A button that
	silently does nothing sends them to Purge instead.
	"""

	FORM_JS = (
		pathlib.Path(__file__).resolve().parents[1]
		/ "hr/doctype/hrms_erp_instance/hrms_erp_instance.js"
	)

	def test_the_method_the_button_calls_exists_and_is_whitelisted(self):
		import re

		js = self.FORM_JS.read_text()
		called = set(re.findall(r"method:\s*[\"']([\w.]*diagnose\.[\w.]+)[\"']", js))
		self.assertTrue(called, "the form no longer calls diagnose — delete this test or fix the wiring")

		tree = ast.parse(SOURCE.read_text())
		whitelisted = {
			n.name
			for n in tree.body
			if isinstance(n, ast.FunctionDef)
			and any(
				"whitelist" in ast.dump(d) for d in n.decorator_list
			)
		}
		for path in called:
			self.assertTrue(
				path.startswith("hrms.sync.diagnose."),
				f"{path} does not point at this module",
			)
			self.assertIn(
				path.rsplit(".", 1)[1],
				whitelisted,
				f"{path} is not a @frappe.whitelist function — the button would fail at the network",
			)


if __name__ == "__main__":
	unittest.main()
