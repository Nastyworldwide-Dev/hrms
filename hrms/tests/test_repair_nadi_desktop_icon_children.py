"""`v16_0.repair_nadi_desktop_icon_children` — putting the launcher back.

The rebrand renamed the parent Desktop Icon "Frappe HR" -> "Nadi" in nine child
fixtures without advancing their `modified`, so Frappe's timestamp gate skipped
the import and the rows kept pointing at the old label. `rename_frappe_hr_desktop_icon`
then found "Nadi" already created by `sync_all` and took its *other* branch:

    frappe.delete_doc("Desktop Icon", "Frappe HR", force=True)

`force=True` skips the link check, so the parent nine live rows pointed at was
removed. `desktop.js:204` then never assembles `child_icons`, and `desktop.js:1123`
degrades the app icon from a workspace modal to a plain link.

The timestamp bump is the primary fix — `sync_all` runs before post_model_sync
patches, so on most sites the fixtures repoint the children before this patch is
reached. This is the backstop for the rest: a row whose `modified` is newer than
the fixture (someone edited it in Desk), and the orphaned "Frappe HR" record
itself, which no fixture can remove.

Properties pinned here:

* registered in `patches.txt` — an unregistered patch never runs;
* children are repointed BEFORE the orphan is deleted. Deleting first is the
  original bug, and order is the whole defect;
* idempotent — a second run touches nothing;
* a fresh site with no "Nadi" is left alone rather than half-repaired;
* only "Frappe HR" children move; anything else keeps its parent.

Bench-free: `frappe` is stubbed in `sys.modules` and the patch is loaded from its
file. Run it as a FILE:

    python3 hrms/tests/test_repair_nadi_desktop_icon_children.py
"""

import importlib.util
import pathlib
import sys
import types
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
PATCH_PATH = HRMS_ROOT / "patches" / "v16_0" / "repair_nadi_desktop_icon_children.py"
PATCHES_TXT = HRMS_ROOT / "patches.txt"
PATCH_DOTTED = "hrms.patches.v16_0.repair_nadi_desktop_icon_children"


class _FakeDB:
	def __init__(self, icons, ops):
		self.icons = icons
		self.ops = ops

	def exists(self, doctype, name):
		return name in self.icons

	def set_value(self, doctype, name, field, value, update_modified=True):
		self.ops.append(("set", name, field, value))
		self.icons[name][field] = value


class _FakeFrappe(types.ModuleType):
	def __init__(self, icons):
		super().__init__("frappe")
		self.icons = icons
		self.ops = []
		self.db = _FakeDB(icons, self.ops)
		self.cache_cleared = 0

	def get_all(self, doctype, filters=None, pluck=None, **kwargs):
		self.ops.append(("get_all", filters))
		return [
			name
			for name, row in self.icons.items()
			if all(row.get(k) == v for k, v in (filters or {}).items())
		]

	def delete_doc(self, doctype, name, **kwargs):
		self.ops.append(("delete", name))
		self.icons.pop(name, None)

	def clear_cache(self, *a, **kw):
		self.cache_cleared += 1

	def logger(self, *a, **kw):
		import logging

		return logging.getLogger("hrms-test")


def load_patch(icons):
	fake = _FakeFrappe(icons)
	sys.modules["frappe"] = fake
	spec = importlib.util.spec_from_file_location(PATCH_DOTTED, PATCH_PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module, fake


def broken_site():
	"""What a live site looks like today: nine orphans, no parent."""
	icons = {"Nadi": {"label": "Nadi", "icon_type": "App", "parent_icon": None}}
	for label in (
		"Leaves",
		"Expenses",
		"Recruitment",
		"Payroll",
		"Performance",
		"Tenure",
		"HR Setup",
		"Shift & Attendance",
		"Tax & Benefits",
	):
		icons[label] = {"label": label, "icon_type": "Link", "parent_icon": "Frappe HR"}
	return icons


class TestRegistration(unittest.TestCase):
	def test_the_patch_is_registered(self):
		self.assertIn(PATCH_DOTTED, PATCHES_TXT.read_text())

	def test_it_runs_after_the_model_sync(self):
		"""It repairs rows, so the schema and the fixtures must land first."""
		text = PATCHES_TXT.read_text()
		post = text.index("[post_model_sync]")
		self.assertGreater(text.index(PATCH_DOTTED), post)


class TestRepair(unittest.TestCase):
	def test_it_repoints_all_nine_children(self):
		icons = broken_site()
		module, _ = load_patch(icons)
		module.execute()
		parents = {row["parent_icon"] for label, row in icons.items() if label != "Nadi"}
		self.assertEqual(parents, {"Nadi"})

	def test_it_repoints_before_deleting_the_orphan(self):
		"""Deleting first is the original bug — it strands the children."""
		icons = broken_site()
		icons["Frappe HR"] = {"label": "Frappe HR", "icon_type": "App", "parent_icon": None}
		module, fake = load_patch(icons)
		module.execute()
		sets = [i for i, op in enumerate(fake.ops) if op[0] == "set"]
		deletes = [i for i, op in enumerate(fake.ops) if op[0] == "delete"]
		self.assertTrue(sets and deletes)
		self.assertLess(max(sets), min(deletes))

	def test_it_removes_the_orphaned_parent(self):
		icons = broken_site()
		icons["Frappe HR"] = {"label": "Frappe HR", "icon_type": "App", "parent_icon": None}
		module, _ = load_patch(icons)
		module.execute()
		self.assertNotIn("Frappe HR", icons)

	def test_a_second_run_changes_nothing(self):
		icons = broken_site()
		module, _ = load_patch(icons)
		module.execute()
		before = {k: dict(v) for k, v in icons.items()}
		module2, fake2 = load_patch(icons)
		module2.execute()
		self.assertEqual(icons, before)
		self.assertEqual([op for op in fake2.ops if op[0] in ("set", "delete")], [])

	def test_a_healthy_site_is_untouched(self):
		icons = {
			"Nadi": {"label": "Nadi", "icon_type": "App", "parent_icon": None},
			"Leaves": {"label": "Leaves", "icon_type": "Link", "parent_icon": "Nadi"},
		}
		module, fake = load_patch(icons)
		module.execute()
		self.assertEqual([op for op in fake.ops if op[0] in ("set", "delete")], [])

	def test_a_site_without_nadi_is_left_alone(self):
		"""Half-repairing a site that never had the rebrand is worse than nothing."""
		icons = {"Leaves": {"label": "Leaves", "icon_type": "Link", "parent_icon": "Frappe HR"}}
		module, fake = load_patch(icons)
		module.execute()
		self.assertEqual(icons["Leaves"]["parent_icon"], "Frappe HR")
		self.assertEqual([op for op in fake.ops if op[0] in ("set", "delete")], [])

	def test_it_does_not_touch_other_parents(self):
		icons = broken_site()
		icons["Elsewhere"] = {"label": "Elsewhere", "icon_type": "Link", "parent_icon": "Accounting"}
		module, _ = load_patch(icons)
		module.execute()
		self.assertEqual(icons["Elsewhere"]["parent_icon"], "Accounting")


if __name__ == "__main__":
	unittest.main()
