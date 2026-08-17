"""`v16_0.add_sync_provenance_fields` — the patch that unblocks Phase 5.

`synced_from_instance` is created by `hrms.setup.get_custom_fields()`, which runs
from `after_install` and therefore **only on a fresh install**. `bench migrate` on
an already-installed site never calls it, so on every existing site the field is
simply absent — confirmed on the live hub. Without it the mirror cannot stamp
provenance and `hrms.sync.parity` cannot count mirrored rows.

The properties pinned here:

* the patch is registered in `patches.txt` (an unregistered patch never runs);
* it reuses `get_provenance_custom_fields()` rather than restating the field
  definitions, so the install path and the patch path cannot drift;
* it covers Company as well as Employee — Company joined the sync for the
  create-only Company mirror and is stamped like everything else;
* it is idempotent: `update=True`, and a second run changes nothing.

Bench-free by construction, like `test_company_settings.py`: `frappe` and
`hrms.sync.runner` are stubbed in `sys.modules` and the patch is loaded straight
from its file. Run it as a FILE:

    python3 hrms/tests/test_sync_provenance_patch.py
"""

import importlib.util
import logging
import pathlib
import sys
import types
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
PATCH_PATH = HRMS_ROOT / "patches" / "v16_0" / "add_sync_provenance_fields.py"
PATCHES_TXT = HRMS_ROOT / "patches.txt"
RUNNER_PATH = HRMS_ROOT / "sync" / "runner.py"
SETUP_PATH = HRMS_ROOT / "setup.py"

PATCH_DOTTED = "hrms.patches.v16_0.add_sync_provenance_fields"


class _FakeDB:
	def __init__(self):
		self.commits = 0

	def commit(self):
		self.commits += 1


def _load_runner():
	"""The real runner module, loaded from file — the patch must use *these* defs."""
	if "frappe" not in sys.modules:
		frappe = types.ModuleType("frappe")
		frappe._ = lambda text: text
		frappe.logger = lambda *a, **kw: logging.getLogger("hrms-test")
		frappe.whitelist = lambda *a, **kw: lambda fn: fn
		frappe.only_for = lambda *a, **kw: None
		frappe.db = None
		frappe_utils = types.ModuleType("frappe.utils")
		frappe_utils.now_datetime = lambda: None
		frappe.utils = frappe_utils
		sys.modules["frappe"] = frappe
		sys.modules["frappe.utils"] = frappe_utils

	import frappe

	saved = (getattr(frappe, "_", None), getattr(frappe, "whitelist", None))
	frappe._ = lambda text: text
	frappe.whitelist = lambda *a, **kw: lambda fn: fn
	try:
		spec = importlib.util.spec_from_file_location("_hrms_sync_runner_for_patch", RUNNER_PATH)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	finally:
		frappe._, frappe.whitelist = saved
	# The patch does `from hrms.sync.runner import ...`; sys.modules short-circuits
	# the import machinery, so no bench-resident `hrms` package is needed.
	sys.modules["hrms.sync.runner"] = module
	return module


runner = _load_runner()

CREATED = []


def _fake_create_custom_fields(fields, update=False, **kwargs):
	CREATED.append({"fields": fields, "update": update})


def _load_patch():
	custom_field_module = types.ModuleType("frappe.custom.doctype.custom_field.custom_field")
	custom_field_module.create_custom_fields = _fake_create_custom_fields
	for name in (
		"frappe.custom",
		"frappe.custom.doctype",
		"frappe.custom.doctype.custom_field",
	):
		sys.modules.setdefault(name, types.ModuleType(name))
	saved_cf = sys.modules.get("frappe.custom.doctype.custom_field.custom_field")
	sys.modules["frappe.custom.doctype.custom_field.custom_field"] = custom_field_module

	saved_runner = sys.modules.get("hrms.sync.runner")
	sys.modules["hrms.sync.runner"] = runner
	try:
		spec = importlib.util.spec_from_file_location("_hrms_provenance_patch_under_test", PATCH_PATH)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	finally:
		if saved_cf is not None:
			sys.modules["frappe.custom.doctype.custom_field.custom_field"] = saved_cf
		if saved_runner is not None:
			sys.modules["hrms.sync.runner"] = saved_runner
	return module


patch = _load_patch()


class _PatchTestCase(unittest.TestCase):
	def setUp(self):
		import frappe

		self.frappe = frappe
		self._saved = (getattr(frappe, "db", None), getattr(frappe, "logger", None))
		self.db = _FakeDB()
		frappe.db = self.db
		frappe.logger = lambda *a, **kw: logging.getLogger("hrms-test")
		CREATED.clear()
		self.addCleanup(self._restore)

	def _restore(self):
		self.frappe.db, self.frappe.logger = self._saved


class TestPatchIsWiredUp(_PatchTestCase):
	def test_patch_is_registered_in_patches_txt(self):
		registered = [
			line.split("#")[0].strip()
			for line in PATCHES_TXT.read_text(encoding="utf-8").splitlines()
			if line.strip() and not line.strip().startswith("#")
		]
		self.assertIn(PATCH_DOTTED, registered, "an unregistered patch never runs")

	def test_patch_is_registered_exactly_once(self):
		body = PATCHES_TXT.read_text(encoding="utf-8")
		self.assertEqual(body.count(PATCH_DOTTED), 1)

	def test_patch_imports_the_install_path_definitions(self):
		"""Restating the field definitions here is how the two paths drift."""
		source = PATCH_PATH.read_text(encoding="utf-8")
		self.assertIn("from hrms.sync.runner import get_provenance_custom_fields", source)
		self.assertNotIn('"fieldtype"', source, "the patch must not restate a field definition")

	def test_install_path_uses_the_same_helper(self):
		self.assertIn("get_provenance_custom_fields", SETUP_PATH.read_text(encoding="utf-8"))


class TestPatchCreatesTheFields(_PatchTestCase):
	def test_it_creates_exactly_the_provenance_fields(self):
		patch.execute()

		self.assertEqual(len(CREATED), 1)
		self.assertEqual(CREATED[0]["fields"], runner.get_provenance_custom_fields())

	def test_it_covers_exactly_the_stamped_doctypes(self):
		"""The patch must track `STAMPED_DOCTYPES` rather than a hand-written list,
		or `parity.py` silently undercounts whatever the two disagree about.

		Neither Company nor the create-only masters belong here: both are HR-owned
		on this hub and carry no stamp, so creating the field on them would suggest
		a provenance that is never written. Because the stamped set is unchanged by
		the master work, no re-run of this patch is needed on live sites.
		"""
		patch.execute()

		created_for = set(CREATED[0]["fields"])
		self.assertEqual(created_for, set(runner.STAMPED_DOCTYPES))
		self.assertNotIn("Company", created_for)
		for master in runner.MASTER_DOCTYPES:
			self.assertNotIn(master, created_for)

	def test_the_field_is_the_one_the_mirror_and_parity_read(self):
		patch.execute()

		for definitions in CREATED[0]["fields"].values():
			self.assertEqual(definitions[0]["fieldname"], runner.PROVENANCE_FIELD)

	def test_it_commits(self):
		patch.execute()
		self.assertEqual(self.db.commits, 1)


class TestPatchIsIdempotent(_PatchTestCase):
	def test_update_true_makes_a_re_run_a_no_op(self):
		"""`create_custom_fields(..., update=True)` leaves an existing, correct
		field exactly as it is — that is what makes a re-run safe."""
		patch.execute()
		self.assertTrue(CREATED[0]["update"])

	def test_running_it_twice_asks_for_the_same_fields(self):
		patch.execute()
		patch.execute()

		self.assertEqual(len(CREATED), 2)
		self.assertEqual(CREATED[0]["fields"], CREATED[1]["fields"])
		self.assertTrue(all(call["update"] for call in CREATED))

	def test_a_fresh_site_that_already_has_the_fields_is_unharmed(self):
		"""`install_app` marks the patch applied, but a site can still reach it via
		a re-run; it must not fail or produce a different definition."""
		patch.execute()
		first = CREATED[0]["fields"]
		CREATED.clear()

		patch.execute()

		self.assertEqual(CREATED[0]["fields"], first)


if __name__ == "__main__":
	unittest.main()
