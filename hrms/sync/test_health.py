"""`hrms.sync.health` — a sync that stops running must say so.

`run_sync` is `@frappe.whitelist(methods=["POST"])` and appears in NO
`scheduler_events` entry: a human presses it or the mirror does not move. The
runner already notifies on a finished run, but `_notify_run_finished` addresses
`frappe.session.user` — whoever pressed the button. So a run that FAILS is
audible, and a run that never happens is silent. Nothing watches the gap.

That gap is the shape of the reported symptom: employee and check-in data that
simply stopped, with no error anywhere, because the last person to press the
button stopped pressing it.

This reports it the way `company_fence.report_unfenced_hr_users` reports its
own holes — an Error Log entry a Desk user can find — rather than inventing a
second channel. It is DETECTIVE only: it never starts a sync. Whether the pull
should be scheduled at all is a product decision about writing to a mirror
unattended, not one to make from a test file.

Bench-free: `frappe` is stubbed. Run it as a FILE:

    python3 hrms/sync/test_health.py
"""

import datetime
import importlib.util
import pathlib
import sys
import types
import unittest

SOURCE = pathlib.Path(__file__).resolve().parent / "health.py"

NOW = datetime.datetime(2026, 8, 26, 3, 0, 0)


def hours_ago(n):
	return NOW - datetime.timedelta(hours=n)


class _FakeFrappe(types.ModuleType):
	def __init__(self, instances, runs):
		super().__init__("frappe")
		self.instances = instances  # [{name, enabled}]
		self.runs = runs  # [{source_instance, status, finished_at}]
		self.errors = []
		self.session = types.SimpleNamespace(user="Administrator")

	def get_all(self, doctype, filters=None, fields=None, pluck=None, order_by=None, limit=None, **kw):
		filters = filters or {}
		if doctype == "HRMS ERP Instance":
			rows = [i for i in self.instances if all(i.get(k) == v for k, v in filters.items())]
			return [r["name"] for r in rows] if pluck else rows
		if doctype == "HRMS Sync Run":
			rows = [r for r in self.runs if all(r.get(k) == v for k, v in filters.items())]
			rows.sort(key=lambda r: r["finished_at"] or NOW, reverse=True)
			if limit:
				rows = rows[:limit]
			# Honour the `fields` contract: the caller asks for `name`, so a row
			# without one is the stub lying, not the code failing. Caught exactly
			# that on first run.
			return [{"name": f"SYNC-{i:05d}", **r} for i, r in enumerate(rows)]
		return []

	def log_error(self, title=None, message=None, **kw):
		self.errors.append({"title": title, "message": message})

	def utils_now(self):
		return NOW


def load(instances, runs):
	fake = _FakeFrappe(instances, runs)
	sys.modules["frappe"] = fake
	utils = types.ModuleType("frappe.utils")
	utils.now_datetime = lambda: NOW
	utils.get_datetime = lambda v: v
	sys.modules["frappe.utils"] = utils
	fake.utils = utils
	spec = importlib.util.spec_from_file_location("sync_health_under_test", SOURCE)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module, fake


ONE = [{"name": "nasty-live", "enabled": 1}]


class TestStaleness(unittest.TestCase):
	def test_a_recent_completed_run_is_healthy(self):
		module, fake = load(
			ONE, [{"source_instance": "nasty-live", "status": "Completed", "finished_at": hours_ago(2)}]
		)
		self.assertEqual(module.report_stale_instances(), [])
		self.assertEqual(fake.errors, [])

	def test_an_old_completed_run_is_reported(self):
		module, fake = load(
			ONE, [{"source_instance": "nasty-live", "status": "Completed", "finished_at": hours_ago(400)}]
		)
		stale = module.report_stale_instances()
		self.assertEqual([s["instance"] for s in stale], ["nasty-live"])
		self.assertEqual(len(fake.errors), 1)

	def test_an_instance_that_has_never_run_is_reported(self):
		"""The worst case, and the one a 'newest run' check alone misses."""
		module, fake = load(ONE, [])
		stale = module.report_stale_instances()
		self.assertEqual([s["reason"] for s in stale], ["never"])
		self.assertEqual(len(fake.errors), 1)

	def test_a_failed_run_does_not_count_as_a_heartbeat(self):
		"""A run that errored is not evidence the mirror moved."""
		module, _ = load(
			ONE,
			[
				{"source_instance": "nasty-live", "status": "Failed", "finished_at": hours_ago(1)},
				{"source_instance": "nasty-live", "status": "Completed", "finished_at": hours_ago(400)},
			],
		)
		self.assertEqual([s["reason"] for s in module.report_stale_instances()], ["stale"])

	def test_a_partial_run_does_not_count_either(self):
		"""Partial means rows were left unwritten and the watermark was held."""
		module, _ = load(
			ONE, [{"source_instance": "nasty-live", "status": "Partial", "finished_at": hours_ago(1)}]
		)
		self.assertEqual([s["reason"] for s in module.report_stale_instances()], ["never"])

	def test_a_disabled_instance_is_not_reported(self):
		"""Turning an instance off is a decision, not a fault."""
		module, fake = load([{"name": "old-erp", "enabled": 0}], [])
		self.assertEqual(module.report_stale_instances(), [])
		self.assertEqual(fake.errors, [])

	def test_every_stale_instance_lands_in_one_report(self):
		"""One Error Log entry, not one per instance — the fence reporter's shape."""
		module, fake = load(
			[{"name": "a", "enabled": 1}, {"name": "b", "enabled": 1}],
			[],
		)
		self.assertEqual(len(module.report_stale_instances()), 2)
		self.assertEqual(len(fake.errors), 1)
		self.assertIn("a", fake.errors[0]["message"])
		self.assertIn("b", fake.errors[0]["message"])

	def test_it_never_starts_a_sync(self):
		"""Detective only. Whether the pull should run unattended is a product
		decision about writing to a mirror without a human present.

		Read from the AST, not the text: the module docstring names `run_sync` to
		explain what it does NOT do, and a substring search cannot tell an
		explanation from a call. (Same trap as test_report_scope_filters.)
		"""
		import ast

		tree = ast.parse(SOURCE.read_text())
		called = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
		imported = {
			alias.name
			for n in ast.walk(tree)
			if isinstance(n, ast.ImportFrom | ast.Import)
			for alias in n.names
		}
		for forbidden in ("run_sync", "queue_sync", "enqueue", "sync_instance"):
			self.assertFalse(any(forbidden in c for c in called), f"{forbidden} is called: {called}")
			self.assertNotIn(forbidden, imported)


if __name__ == "__main__":
	unittest.main()
