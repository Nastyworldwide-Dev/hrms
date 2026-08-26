"""The overlap guard is one-directional, and nothing said so until this file.

Two systems can write leave for the same employee during the parallel run, and
`validate_leave_overlap` is the only thing standing between that and a
double-counted balance. It runs on `validate`. So:

    submitted HERE, overlapping a mirrored row .... guard runs, blocked
    pulled FROM THE SOURCE, overlapping a hub row .. guard NEVER RUNS

The second line is not an oversight in the sync. `runner._write_row` sets
`doc.flags.ignore_validate = True` deliberately, and it has to: a mirror that
refuses a row is a mirror that lies about what the source holds. Rejecting the
pull would trade a visible duplicate for an invisible omission, which is worse
— the hub would look consistent while quietly missing leave the source has
already approved and the employee has already taken.

So the collision is allowed to land, and then it is NAMED. Detective, not
preventive — the same contract as the staleness heartbeat next door, for the
same reason: this module never decides what the mirror should contain.

That leaves a real ceiling worth stating rather than hiding. Between the pull
landing and someone reading the report, the employee's balance IS wrong on this
hub. This narrows the window from "for ever, silently" to "until the next daily
report", which is an improvement and is not a fix. The fix is cutover — one
writer, no collisions possible, and this whole file deletes.

Bench-free: `frappe` is stubbed. Run it as a FILE:

    python3 hrms/sync/test_leave_collision.py
"""

import importlib.util
import pathlib
import sys
import types
import unittest

SOURCE = pathlib.Path(__file__).resolve().parent / "health.py"

STAMP = "synced_from_instance"


class _FakeFrappe(types.ModuleType):
	def __init__(self, sql_rows):
		super().__init__("frappe")
		self.sql_rows = sql_rows
		self.queries: list[tuple] = []
		self.errors: list[dict] = []
		self.session = types.SimpleNamespace(user="Administrator")

	class _DB:
		def __init__(self, outer):
			self.outer = outer

		def sql(self, query, values=None, as_dict=False):
			self.outer.queries.append((" ".join(query.split()), values))
			return self.outer.sql_rows

	def __getattr__(self, name):
		if name == "db":
			db = _FakeFrappe._DB(self)
			object.__setattr__(self, "db", db)
			return db
		raise AttributeError(name)

	def get_all(self, *a, **kw):
		return []

	def log_error(self, title=None, message=None, **kw):
		self.errors.append({"title": title, "message": message})


def load(sql_rows=()):
	fake = _FakeFrappe(list(sql_rows))
	sys.modules["frappe"] = fake
	fake._ = lambda s: s

	utils = types.ModuleType("frappe.utils")
	utils.now_datetime = lambda: None
	utils.get_datetime = lambda v: v
	sys.modules["frappe.utils"] = utils

	spec = importlib.util.spec_from_file_location("health_under_test", SOURCE)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module, fake


#: One employee, two overlapping approved leaves — one mirrored from the source,
#: one written here. The exact shape that double-counts a balance.
COLLISION = [
	{
		"employee": "HR-EMP-00042",
		"employee_name": "Mirza",
		"mirrored": "HR-LAP-2026-00311",
		"instance": "Nasty-Live",
		"local": "HR-LAP-2026-00998",
		"from_date": "2026-09-01",
		"to_date": "2026-09-03",
	}
]


class TestTheCollisionIsFound(unittest.TestCase):
	def test_an_overlapping_pair_is_reported(self):
		module, _ = load(COLLISION)
		found = module.colliding_leave()
		self.assertEqual(len(found), 1)
		self.assertEqual(found[0]["employee"], "HR-EMP-00042")

	def test_a_clean_hub_reports_nothing(self):
		module, _ = load([])
		self.assertEqual(module.colliding_leave(), [])

	def test_it_reaches_the_daily_report(self):
		module, fake = load(COLLISION)
		module.report_stale_instances()
		self.assertTrue(
			any("leave" in (e["title"] or "").lower() for e in fake.errors),
			f"no collision Error Log was written; got {[e['title'] for e in fake.errors]}",
		)

	def test_the_report_names_the_employee_and_both_rows(self):
		"""An operator has to be able to open the two records and rule on them.

		A count ("1 collision") is not actionable, and this report is the only
		thing that will ever mention the pair."""
		module, fake = load(COLLISION)
		module.report_stale_instances()
		body = "\n".join(e["message"] or "" for e in fake.errors)
		for token in ("Mirza", "HR-LAP-2026-00311", "HR-LAP-2026-00998", "2026-09-01"):
			self.assertIn(token, body)

	def test_a_clean_hub_writes_no_error_log(self):
		module, fake = load([])
		module.report_stale_instances()
		self.assertEqual(fake.errors, [])


class TestThePredicate(unittest.TestCase):
	"""The query is read from the SQL the module actually sends.

	Grepping this module's own SOURCE for these clauses would pass on the
	docstrings that explain them — that mistake was made twice in this project
	already (`test_report_scope_filters`, then `test_health`) and is not being
	made a third time. `_FakeFrappe._DB.sql` records the statement, so these
	assertions read the executed text.
	"""

	def setUp(self):
		module, fake = load(COLLISION)
		module.colliding_leave()
		self.sql = fake.queries[0][0]

	def test_one_side_is_mirrored_and_the_other_is_not(self):
		"""Two mirrored rows colliding is the SOURCE's own duplicate, not ours;
		two hub rows colliding is what validate_leave_overlap already blocks."""
		self.assertIn("mirrored.synced_from_instance IS NOT NULL", self.sql)
		self.assertIn("local.synced_from_instance IS NULL", self.sql)

	def test_it_matches_the_guard_it_stands_in_for(self):
		"""Same predicate as validate_leave_overlap: live rows, real statuses,
		ranges that touch. A looser one cries wolf; a tighter one misses the
		case the guard would have caught."""
		self.assertIn("docstatus < 2", self.sql)
		self.assertIn("'Open'", self.sql)
		self.assertIn("'Approved'", self.sql)
		self.assertIn("mirrored.to_date >= local.from_date", self.sql)
		self.assertIn("mirrored.from_date <= local.to_date", self.sql)

	def test_it_only_compares_an_employee_against_themselves(self):
		self.assertIn("mirrored.employee = local.employee", self.sql)

	def test_the_pair_is_reported_once_not_twice(self):
		"""Without an ordering the self-join returns (a,b) AND (b,a), so every
		collision would be named twice and the count would be double."""
		self.assertIn("mirrored.name != local.name", self.sql)


if __name__ == "__main__":
	unittest.main()
