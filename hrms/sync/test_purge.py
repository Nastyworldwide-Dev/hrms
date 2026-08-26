"""`hrms.sync.purge` — removing what a mirror pulled, without removing anything else.

The write-block was never what stopped this. Reproduced on a bench: a System
Manager deleting a mirrored Employee gets `ALLOW_OVERRIDE` from
`plan_mirror_write`, the override is logged, and then Frappe's own link
validation refuses:

    LinkExistsError: Cannot delete ... Employee HR-EMP-00001 is linked with
    Employee Checkin EMP-CKIN-08-2026-000001

Employee is the last thing the sync writes and therefore the first thing
everything else points at. Deleting it needs its mirrored Attendance, Employee
Checkin, Leave Ledger Entry and the rest gone first — and each of THOSE is
write-blocked too, so the operator is left bulk-deleting in dependency order by
hand and reading "Bulk Operation Failed: 107 documents" with no reason attached.

`runner.py` already counts local orphans and says deletion "is out of scope; a
divergence is for a human". This is the tool that human never had.

The properties pinned here, in the order they matter:

* it deletes ONLY rows carrying this instance's provenance stamp - never a
  local row, never another instance's;
* it deletes in REVERSE sync order, children before the masters they link to;
* a row blocked by a LOCAL document linking to it is REPORTED, not forced.
  That is the R2 case - a hub-side leave application against a mirrored
  employee - and force-deleting through it would destroy hub-owned data to
  tidy a mirror;
* it is dry-run unless the caller types the instance name back.

Bench-free: `frappe` is stubbed. Run it as a FILE:

    python3 hrms/sync/test_purge.py
"""

import ast
import importlib.util
import pathlib
import sys
import types
import unittest

SOURCE = pathlib.Path(__file__).resolve().parent / "purge.py"

INSTANCE = "Nasty-Dev"
STAMP = "synced_from_instance"


class _LinkExistsError(Exception):
	pass


class _FakeFrappe(types.ModuleType):
	def __init__(self, rows, blocked=()):
		super().__init__("frappe")
		#: {doctype: [{name, synced_from_instance}]}
		self.rows = rows
		#: names that raise LinkExistsError on delete (a LOCAL doc links to them)
		self.blocked = set(blocked)
		self.deleted = []
		self.errors = []
		self.only_for_calls = []
		self.session = types.SimpleNamespace(user="Administrator")
		self.LinkExistsError = _LinkExistsError
		self.ValidationError = ValueError
		# the decorator must be a pass-through here: this test drives the
		# function directly, not through Frappe's dispatcher
		self.whitelist = lambda **kw: (lambda fn: fn)

		class _DB:
			@staticmethod
			def commit():
				pass

		self.db = _DB()

	def only_for(self, roles):
		self.only_for_calls.append(roles)

	def get_all(self, doctype, filters=None, pluck=None, **kw):
		filters = filters or {}
		out = [r for r in self.rows.get(doctype, []) if all(r.get(k) == v for k, v in filters.items())]
		return [r["name"] for r in out] if pluck else out

	def delete_doc(self, doctype, name, **kw):
		if name in self.blocked:
			raise _LinkExistsError(f"Cannot delete {name}: a local document links to it")
		self.rows[doctype] = [r for r in self.rows.get(doctype, []) if r["name"] != name]
		self.deleted.append((doctype, name))

	def log_error(self, title=None, message=None, **kw):
		self.errors.append({"title": title, "message": message})

	def throw(self, msg, exc=None):
		raise (exc or Exception)(msg)

	def _dict(self, *a, **kw):
		return dict(*a, **kw)


def load(rows, blocked=()):
	fake = _FakeFrappe(rows, blocked)
	sys.modules["frappe"] = fake
	fake._ = lambda s: s
	sys.modules["frappe"]._ = lambda s: s

	utils = types.ModuleType("frappe.utils")
	utils.now_datetime = lambda: None
	sys.modules["frappe.utils"] = utils

	scope = types.ModuleType("hrms.overrides.company_scope")
	scope.require_unfenced = lambda *a, **kw: None
	sys.modules["hrms.overrides.company_scope"] = scope

	runner = types.ModuleType("hrms.sync.runner")
	# masters first, exactly as the runner orders them — the purge must SKIP them
	runner.MASTER_DOCTYPES = ("Department", "Shift Type")
	runner.STAMPED_DOCTYPES = ("Employee", "Attendance", "Employee Checkin")
	runner.DEFAULT_SYNC_DOCTYPES = runner.MASTER_DOCTYPES + runner.STAMPED_DOCTYPES
	runner.PROVENANCE_FIELD = STAMP
	sys.modules["hrms.sync.runner"] = runner

	spec = importlib.util.spec_from_file_location("purge_under_test", SOURCE)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module, fake


def mirrored_site():
	"""One mirrored employee with a mirrored check-in, plus rows that must survive."""
	return {
		# a master. HR-owned, carries no provenance column at all, must survive.
		"Department": [{"name": "Sales - NCIG"}],
		"Employee": [
			{"name": "HR-EMP-00001", STAMP: INSTANCE},
			{"name": "HR-EMP-00002", STAMP: "Other-Instance"},  # another mirror
			{"name": "HR-EMP-LOCAL", STAMP: None},  # hub-owned
		],
		"Attendance": [{"name": "ATT-1", STAMP: INSTANCE}],
		"Employee Checkin": [{"name": "CKIN-1", STAMP: INSTANCE}],
	}


class TestScope(unittest.TestCase):
	def test_it_touches_only_this_instances_rows(self):
		module, fake = load(mirrored_site())
		module.purge_instance(INSTANCE, confirm=INSTANCE)
		survivors = {r["name"] for r in fake.rows["Employee"]}
		self.assertEqual(survivors, {"HR-EMP-00002", "HR-EMP-LOCAL"})

	def test_a_local_row_is_never_deleted(self):
		module, fake = load(mirrored_site())
		module.purge_instance(INSTANCE, confirm=INSTANCE)
		self.assertNotIn(("Employee", "HR-EMP-LOCAL"), fake.deleted)

	def test_another_instances_mirror_is_never_deleted(self):
		module, fake = load(mirrored_site())
		module.purge_instance(INSTANCE, confirm=INSTANCE)
		self.assertNotIn(("Employee", "HR-EMP-00002"), fake.deleted)


class TestOrder(unittest.TestCase):
	def test_children_go_before_the_masters_they_link_to(self):
		"""The whole reason the manual delete failed: Employee is written last
		and pointed at by everything, so it must be removed last too."""
		module, fake = load(mirrored_site())
		module.purge_instance(INSTANCE, confirm=INSTANCE)
		order = [d for d, _ in fake.deleted]
		self.assertLess(order.index("Employee Checkin"), order.index("Employee"))
		self.assertLess(order.index("Attendance"), order.index("Employee"))
		self.assertNotIn("Department", order, "a master is HR-owned and must never be purged")


class TestSafety(unittest.TestCase):
	def test_it_is_a_dry_run_without_the_typed_confirmation(self):
		module, fake = load(mirrored_site())
		result = module.purge_instance(INSTANCE)
		self.assertEqual(fake.deleted, [])
		self.assertTrue(result["dry_run"])
		self.assertEqual(result["counts"]["Employee"], 1)

	def test_a_wrong_confirmation_deletes_nothing(self):
		module, fake = load(mirrored_site())
		with self.assertRaises(Exception):
			module.purge_instance(INSTANCE, confirm="nasty-dev")
		self.assertEqual(fake.deleted, [])

	def test_it_is_system_manager_only(self):
		module, fake = load(mirrored_site())
		module.purge_instance(INSTANCE)
		self.assertTrue(fake.only_for_calls, "purge must call frappe.only_for")
		self.assertIn("System Manager", str(fake.only_for_calls[0]))

	def test_a_row_a_local_document_links_to_is_reported_not_forced(self):
		"""R2: a hub-side leave application against a mirrored employee. Forcing
		through it would destroy hub-owned data to tidy a mirror."""
		module, fake = load(mirrored_site(), blocked={"HR-EMP-00001"})
		result = module.purge_instance(INSTANCE, confirm=INSTANCE)
		self.assertEqual(result["blocked"][0]["name"], "HR-EMP-00001")
		self.assertIn("HR-EMP-00001", {n for _, n in fake.deleted} ^ {"HR-EMP-00001"})
		self.assertNotIn(("Employee", "HR-EMP-00001"), fake.deleted)

	def test_it_never_passes_force(self):
		"""force=True skips the link check — the one thing standing between a
		mirror cleanup and deleting hub-owned records."""
		tree = ast.parse(SOURCE.read_text())
		for node in ast.walk(tree):
			if isinstance(node, ast.Call) and "delete_doc" in ast.unparse(node.func):
				kwargs = {k.arg for k in node.keywords}
				self.assertNotIn("force", kwargs, ast.unparse(node))

	def test_it_records_what_it_did(self):
		module, fake = load(mirrored_site())
		module.purge_instance(INSTANCE, confirm=INSTANCE)
		self.assertTrue(fake.errors, "a destructive run must leave an audit entry")


if __name__ == "__main__":
	unittest.main()
