"""Releasing a stamp is the recovery Purge is not, and the guard needs it.

`plan_cross_instance_write` stops a second instance overwriting a first one's
rows. It is also, on a hub that already ran two colliding instances, in the way
of putting things right: rows currently stamped `Nasty-Dev` that are really
LIVE employees will be refused when Nasty-Live next syncs, because dev got there
first. The guard would block the very repair it exists to make unnecessary.

Purge cannot be that repair. It deletes by the stamp, and the stamp is the thing
that is wrong — that is exactly how a real record was lost here.

So: release the STAMP, not the rows. Clearing `synced_from_instance` turns a
mirrored row into a hub-owned one, and `plan_cross_instance_write` already lets
the first writer take an unstamped row. The next full sync from live then
reclaims everything live genuinely holds and rewrites its content, and whatever
is left unstamped afterwards is the answer to the question nobody could answer:
which rows only ever existed on dev.

It deletes nothing. That is the entire point — after this project lost a record
to a destructive fix, the recovery tool has to be one that cannot lose another.

Bench-free: `frappe` is stubbed. Run it as a FILE:

    python3 hrms/sync/test_release.py
"""

import importlib.util
import pathlib
import sys
import types
import unittest

SOURCE = pathlib.Path(__file__).resolve().parent / "purge.py"

STAMP = "synced_from_instance"
CLONE = "Nasty-Dev"
LIVE = "Nasty-Live"


class _FakeFrappe(types.ModuleType):
	def __init__(self, rows):
		super().__init__("frappe")
		self.rows = rows  # {doctype: [{"name": str, STAMP: str|None}]}
		self.deleted: list[tuple] = []
		self.committed = 0
		self.session = types.SimpleNamespace(user="Administrator")
		self.ValidationError = type("ValidationError", (Exception,), {})
		self.LinkExistsError = type("LinkExistsError", (Exception,), {})

	class _DB:
		def __init__(self, outer):
			self.outer = outer

		def set_value(self, doctype, name, field, value=None, update_modified=True):
			for row in self.outer.rows.get(doctype, []):
				if row["name"] == name:
					if isinstance(field, dict):
						row.update(field)
					else:
						row[field] = value

		def commit(self):
			self.outer.committed += 1

		def get_value(self, doctype, name, field):
			for row in self.outer.rows.get(doctype, []):
				if row["name"] == name:
					return row.get(field)
			return None

	def __getattr__(self, name):
		if name == "db":
			db = _FakeFrappe._DB(self)
			object.__setattr__(self, "db", db)
			return db
		raise AttributeError(name)

	def get_all(self, doctype, filters=None, pluck=None, **kw):
		want = (filters or {}).get(STAMP)
		return [r["name"] for r in self.rows.get(doctype, []) if r.get(STAMP) == want]

	def only_for(self, *a, **kw):
		pass

	def whitelist(self, *a, **kw):
		return lambda fn: fn

	def throw(self, msg, exc=None, **kw):
		raise (exc or Exception)(msg)

	def delete_doc(self, doctype, name, **kw):
		self.deleted.append((doctype, name))


def load(rows):
	fake = _FakeFrappe(rows)
	sys.modules["frappe"] = fake
	fake._ = lambda s: s

	scope = types.ModuleType("hrms.overrides.company_scope")
	scope.require_unfenced = lambda *a, **kw: None
	sys.modules["hrms.overrides.company_scope"] = scope

	runner = types.ModuleType("hrms.sync.runner")
	runner.STAMPED_DOCTYPES = ("Employee", "Attendance")
	runner.PROVENANCE_FIELD = STAMP
	sys.modules["hrms.sync.runner"] = runner

	spec = importlib.util.spec_from_file_location("purge_under_test", SOURCE)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module, fake


def hub_with_a_clone():
	"""What the live hub actually looks like: dev stamped some of live's rows."""
	return {
		"Employee": [
			{"name": "HR-EMP-00001", STAMP: LIVE},
			{"name": "HR-EMP-00002", STAMP: CLONE},  # really a live employee
			{"name": "HR-EMP-00003", STAMP: CLONE},
			{"name": "HR-EMP-00004", STAMP: None},  # written on the hub
		],
		"Attendance": [{"name": "ATT-1", STAMP: CLONE}],
	}


class TestItReleasesTheRightRows(unittest.TestCase):
	def test_the_clone_stamp_is_cleared(self):
		module, fake = load(hub_with_a_clone())
		module.release_instance_stamp(CLONE, confirm=CLONE)
		stamps = [r[STAMP] for r in fake.rows["Employee"]]
		self.assertEqual(stamps, [LIVE, None, None, None])

	def test_another_instances_rows_are_untouched(self):
		module, fake = load(hub_with_a_clone())
		module.release_instance_stamp(CLONE, confirm=CLONE)
		self.assertEqual(fake.rows["Employee"][0][STAMP], LIVE)

	def test_every_stamped_doctype_is_covered(self):
		module, fake = load(hub_with_a_clone())
		module.release_instance_stamp(CLONE, confirm=CLONE)
		self.assertIsNone(fake.rows["Attendance"][0][STAMP])

	def test_it_reports_what_it_released(self):
		module, _ = load(hub_with_a_clone())
		out = module.release_instance_stamp(CLONE, confirm=CLONE)
		self.assertEqual(out["counts"], {"Employee": 2, "Attendance": 1})
		self.assertEqual(out["total"], 3)


class TestItDeletesNothing(unittest.TestCase):
	"""The whole reason this exists rather than reaching for Purge again."""

	def test_no_row_is_deleted(self):
		module, fake = load(hub_with_a_clone())
		module.release_instance_stamp(CLONE, confirm=CLONE)
		self.assertEqual(fake.deleted, [])

	def test_the_row_count_is_unchanged(self):
		module, fake = load(hub_with_a_clone())
		before = {k: len(v) for k, v in fake.rows.items()}
		module.release_instance_stamp(CLONE, confirm=CLONE)
		self.assertEqual({k: len(v) for k, v in fake.rows.items()}, before)


class TestTheConfirmation(unittest.TestCase):
	"""Same shape as purge_instance: a dry run unless the name is typed back.

	Less destructive, not undoable — once the stamp is gone, which instance a row
	came from is no longer recorded anywhere."""

	def test_no_confirm_is_a_dry_run(self):
		module, fake = load(hub_with_a_clone())
		out = module.release_instance_stamp(CLONE)
		self.assertTrue(out["dry_run"])
		self.assertEqual(out["counts"], {"Employee": 2, "Attendance": 1})
		self.assertEqual(fake.rows["Employee"][1][STAMP], CLONE, "a dry run must change nothing")

	def test_a_wrong_confirmation_is_refused(self):
		module, fake = load(hub_with_a_clone())
		with self.assertRaises(fake.ValidationError):
			module.release_instance_stamp(CLONE, confirm="nasty-dev")
		self.assertEqual(fake.rows["Employee"][1][STAMP], CLONE)


class TestTheStampDoesNotMoveTheTimestamp(unittest.TestCase):
	def test_modified_is_not_bumped(self):
		"""`modified` drives the incremental watermark. Bumping 40,000 rows here
		would make the next sync re-read a window it has already covered — and
		on the mirrored doctypes it would look like the source had changed
		everything at once."""
		module, fake = load(hub_with_a_clone())
		seen = []
		original = fake.db.set_value
		fake.db.set_value = lambda *a, **kw: (
			seen.append(kw.get("update_modified", True)),
			original(*a, **kw),
		)[1]
		module.release_instance_stamp(CLONE, confirm=CLONE)
		self.assertTrue(seen, "nothing was written")
		self.assertNotIn(True, seen, "update_modified must be False on every write")


if __name__ == "__main__":
	unittest.main()
