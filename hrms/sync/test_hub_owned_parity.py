"""Parity must report what this hub OWNS, not only what it copied.

`_local_count` filters on `synced_from_instance`, so it counts mirrored rows and
nothing else. That is correct for measuring the mirror — and it means a doctype
can read "in parity" while the two systems genuinely disagree.

The case is not hypothetical. Leave Application is mirrored AND staff apply for
leave here, so every hub-side application is a row the source does not have and
the gate cannot see. Approve fifty leaves in Nadi and parity still says
`312 / 312 · in parity`, while the hub holds fifty leave records the source has
never heard of.

That matters because parity is not decoration: `is_cutover_ready` counts clean
runs off it to decide when this hub becomes the system of record. A gate that
answers "did I copy correctly?" is being read as "do these two agree?" — and
those are different questions the moment anything is written locally.

So `local_own` is reported ALONGSIDE the mirrored count, never folded into the
delta. Folding it in would be worse than silence: a hub-owned row is not a
missing mirrored row, and adding it to the comparison would make a divergence
look like parity.

Bench-free: `frappe` is stubbed. Run it as a FILE:

    python3 hrms/sync/test_hub_owned_parity.py
"""

import importlib.util
import pathlib
import sys
import types
import unittest

SOURCE = pathlib.Path(__file__).resolve().parent / "parity.py"

INSTANCE = "Nasty-Live"
STAMP = "synced_from_instance"


class _FakeFrappe(types.ModuleType):
	def __init__(self, rows):
		super().__init__("frappe")
		#: {doctype: [{synced_from_instance: str|None, company: str|None}]}
		self.rows = rows
		self.session = types.SimpleNamespace(user="Administrator")

	class _DB:
		def __init__(self, outer):
			self.outer = outer

		def count(self, doctype, filters=None):
			filters = filters or {}
			out = []
			for row in self.outer.rows.get(doctype, []):
				ok = True
				for key, value in filters.items():
					if isinstance(value, list | tuple) and len(value) == 2 and value[0] == "is":
						# ("is", "not set") — the hub-owned predicate
						ok = ok and not row.get(key)
					else:
						ok = ok and row.get(key) == value
				if ok:
					out.append(row)
			return len(out)

	def __getattr__(self, name):
		if name == "db":
			db = _FakeFrappe._DB(self)
			object.__setattr__(self, "db", db)
			return db
		raise AttributeError(name)

	def only_for(self, *a, **kw):
		pass

	def get_all(self, *a, **kw):
		return []

	def whitelist(self, *a, **kw):
		return lambda fn: fn

	def throw(self, msg, *a, **kw):
		raise Exception(msg)


def load(rows):
	fake = _FakeFrappe(rows)
	sys.modules["frappe"] = fake
	fake._ = lambda s: s

	utils = types.ModuleType("frappe.utils")
	utils.now_datetime = lambda: None
	utils.get_datetime = lambda v: v
	sys.modules["frappe.utils"] = utils

	scope = types.ModuleType("hrms.overrides.company_scope")
	scope.require_unfenced = lambda *a, **kw: None
	sys.modules["hrms.overrides.company_scope"] = scope

	spec = importlib.util.spec_from_file_location("parity_under_test", SOURCE)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module, fake


#: 3 mirrored leave applications and 2 written here — the shape that reads
#: "in parity" today while the two systems hold different data.
SPLIT = {
	"Leave Application": [
		{STAMP: INSTANCE},
		{STAMP: INSTANCE},
		{STAMP: INSTANCE},
		{STAMP: None},
		{STAMP: None},
	]
}


class TestHubOwnedIsCounted(unittest.TestCase):
	def test_hub_owned_rows_are_reported(self):
		module, _ = load(SPLIT)
		self.assertEqual(module._local_own_count("Leave Application", None, INSTANCE), 2)

	def test_a_hub_with_nothing_of_its_own_reports_zero(self):
		module, _ = load({"Leave Application": [{STAMP: INSTANCE}, {STAMP: INSTANCE}]})
		self.assertEqual(module._local_own_count("Leave Application", None, INSTANCE), 0)

	def test_another_instances_mirror_is_not_counted_as_hub_owned(self):
		"""A row stamped by a DIFFERENT instance belongs to that mirror, not here."""
		module, _ = load({"Leave Application": [{STAMP: "Nasty-Dev"}, {STAMP: None}]})
		self.assertEqual(module._local_own_count("Leave Application", None, INSTANCE), 1)


class TestDeltaIsUnchanged(unittest.TestCase):
	"""Hub-owned rows are reported, never folded into the comparison.

	Adding them to `local` would make a divergence look like parity, which is
	the opposite of what this line exists to show."""

	def test_hub_owned_rows_do_not_change_the_delta(self):
		module, _ = load(SPLIT)
		line = module.ParityLine("Leave Application", remote=3, local=3, local_own=2)
		self.assertEqual(line.delta, 0)
		self.assertTrue(line.in_parity)

	def test_the_count_reaches_the_report(self):
		module, _ = load(SPLIT)
		line = module.ParityLine("Leave Application", remote=3, local=3, local_own=2)
		self.assertEqual(line.as_dict()["local_own"], 2)

	def test_it_defaults_to_zero_for_callers_that_do_not_pass_it(self):
		module, _ = load(SPLIT)
		self.assertEqual(module.ParityLine("Employee", remote=1, local=1).as_dict()["local_own"], 0)


if __name__ == "__main__":
	unittest.main()
