"""The checkpoint round-trip, against a real database.

`hrms/tests/test_sync_runner.py` is the exhaustive suite for this module and it
is bench-free by design — it loads `runner.py` from its path with a stub
`frappe`, so it can pin every decision without a site. What it necessarily fakes
is the half of the loop where the incident lived: `_finish_run` writing a real
`HRMS Sync Run` row, and `get_watermark` reading that row back.

A run reported `Completed`, `get_watermark` accepted it, the checkpoint advanced
from its stored `started_at`, and an employee the source had returned was never
requested again. These tests exercise that persistence for real. They
deliberately create no Employee and no Company: `sync_instance` commits as it
goes, so savepoint isolation cannot hold, and the heavy end-to-end scenarios are
already covered bench-free where rollback is free.

Bench-backed. Run with:
    bench --site <site> run-tests --module hrms.sync.test_runner
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from hrms.sync.runner import PAGE_ORDER, get_watermark, sync_instance

INSTANCE = "test-sync-checkpoint"


class EmptyRemote:
	"""The `RemoteInstanceClient` contract, returning nothing. Read-only by
	construction — it has no method that could write to any source."""

	def __init__(self, instance_name: str = INSTANCE):
		self.instance_name = instance_name
		self.calls: list[dict] = []

	def get_list(self, doctype, filters=None, fields=None, limit=None, start=0, order_by=None):
		self.calls.append({"doctype": doctype, "filters": filters, "start": start, "order_by": order_by})
		return []


def make_run(status: str, started_at, **counts) -> str:
	doc = frappe.get_doc(
		{
			"doctype": "HRMS Sync Run",
			"source_instance": INSTANCE,
			"status": status,
			"started_at": started_at,
			**counts,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc.name


class TestCheckpointPersistence(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(self.clean)
		self.clean()
		if not frappe.db.exists("HRMS ERP Instance", INSTANCE):
			doc = frappe.get_doc(
				{
					"doctype": "HRMS ERP Instance",
					"instance_name": INSTANCE,
					"url": f"https://{INSTANCE}.example.com",
					"enabled": 1,
				}
			)
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
			frappe.db.commit()

	def clean(self):
		"""Explicit, because `sync_instance` commits — nothing here can be rolled
		back by the test framework."""
		frappe.set_user("Administrator")
		frappe.db.delete("HRMS Sync Run", {"source_instance": INSTANCE})
		frappe.db.delete("HRMS ERP Instance Company", {"parent": INSTANCE})
		frappe.db.delete("HRMS ERP Instance", {"name": INSTANCE})
		frappe.db.commit()

	# --- what get_watermark accepts -----------------------------------------

	def test_only_a_completed_run_advances_the_checkpoint(self):
		make_run("Completed", "2026-08-05 00:00:00")
		make_run("Failed", "2026-08-08 00:00:00")

		self.assertEqual(str(get_watermark(INSTANCE)), "2026-08-05 00:00:00")

	def test_a_partial_run_does_not_advance_the_checkpoint(self):
		"""The fix's whole mechanism: a run that left rows unwritten is Partial,
		and Partial is exactly what `get_watermark` refuses."""
		make_run("Partial", "2026-08-09 00:00:00", rows_orphaned=1)

		self.assertIsNone(get_watermark(INSTANCE))

	def test_a_partial_run_does_not_shadow_an_older_completed_one(self):
		make_run("Completed", "2026-08-05 00:00:00")
		make_run("Partial", "2026-08-09 00:00:00", rows_orphaned=1)

		self.assertEqual(
			str(get_watermark(INSTANCE)),
			"2026-08-05 00:00:00",
			"the checkpoint must fall back to the last run that really finished",
		)

	def test_no_run_at_all_means_a_full_pull(self):
		self.assertIsNone(get_watermark(INSTANCE))

	# --- what _finish_run persists ------------------------------------------

	def test_the_unwritten_counts_survive_a_round_trip(self):
		"""These two columns are new. If they do not persist, an operator is back
		to reading `Completed` and nothing else."""
		name = make_run("Partial", now_datetime(), rows_orphaned=7, rows_errored=3)

		row = frappe.db.get_value(
			"HRMS Sync Run", name, ["rows_orphaned", "rows_errored", "status"], as_dict=True
		)

		self.assertEqual(row.rows_orphaned, 7)
		self.assertEqual(row.rows_errored, 3)
		self.assertEqual(row.status, "Partial")

	def test_a_real_run_records_itself_and_its_counts(self):
		client = EmptyRemote()

		result = sync_instance(client, doctypes=["Employee"], incremental=True)

		row = frappe.db.get_value(
			"HRMS Sync Run",
			result["run"],
			["status", "rows_pulled", "rows_written", "rows_orphaned", "rows_errored"],
			as_dict=True,
		)
		self.assertEqual(row.status, "Completed")
		self.assertEqual(row.rows_pulled, 0)
		self.assertEqual(row.rows_orphaned, 0)
		self.assertEqual(row.rows_errored, 0)

	def test_a_clean_run_is_then_readable_as_the_checkpoint(self):
		"""Closes the loop: the run this module wrote is the run it reads back."""
		result = sync_instance(EmptyRemote(), doctypes=["Employee"], incremental=True)

		started = frappe.db.get_value("HRMS Sync Run", result["run"], "started_at")
		self.assertEqual(get_watermark(INSTANCE), started)

	# --- what reaches the remote --------------------------------------------

	def test_the_checkpoint_reaches_the_remote_as_a_modified_filter(self):
		make_run("Completed", "2026-08-05 00:00:00")
		# read it BEFORE the run: sync_instance writes its own run record, which
		# would otherwise be the row this assertion reads back
		expected = get_watermark(INSTANCE)
		client = EmptyRemote()

		sync_instance(client, doctypes=["Employee"], incremental=True)

		self.assertEqual(client.calls[0]["filters"], {"modified": (">", expected)})

	def test_a_full_pull_ignores_the_checkpoint(self):
		"""The documented recovery for a site whose checkpoint already moved past
		a dropped employee."""
		make_run("Completed", "2026-08-05 00:00:00")
		client = EmptyRemote()

		sync_instance(client, doctypes=["Employee"], incremental=False)

		self.assertIsNone(client.calls[0]["filters"], "a full pull must not filter on modified")

	def test_every_page_asks_for_a_unique_total_order(self):
		"""Offset pagination over `modified` alone can drop a row at a page
		boundary when the source bulk-updates."""
		client = EmptyRemote()

		sync_instance(client, doctypes=["Employee"], incremental=False)

		self.assertEqual(client.calls[0]["order_by"], PAGE_ORDER)
		self.assertIn("name", PAGE_ORDER)


class TestStaleCheckpointRecovery(FrappeTestCase):
	"""A site already past the incident: its last run says Completed even though
	rows were dropped. The recovery has to work without editing history."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(self.clean)
		self.clean()
		doc = frappe.get_doc(
			{
				"doctype": "HRMS ERP Instance",
				"instance_name": INSTANCE,
				"url": f"https://{INSTANCE}.example.com",
				"enabled": 1,
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		make_run("Completed", add_to_date(now_datetime(), days=-1))
		frappe.db.commit()

	def clean(self):
		frappe.set_user("Administrator")
		frappe.db.delete("HRMS Sync Run", {"source_instance": INSTANCE})
		frappe.db.delete("HRMS ERP Instance Company", {"parent": INSTANCE})
		frappe.db.delete("HRMS ERP Instance", {"name": INSTANCE})
		frappe.db.commit()

	def test_a_stale_checkpoint_is_bypassed_by_a_full_pull(self):
		client = EmptyRemote()
		self.assertIsNotNone(get_watermark(INSTANCE), "the stale checkpoint must be in place")

		sync_instance(client, doctypes=["Employee"], incremental=False)

		self.assertIsNone(client.calls[0]["filters"])

	def test_an_explicit_since_also_overrides_it(self):
		client = EmptyRemote()

		sync_instance(client, doctypes=["Employee"], since="2020-01-01 00:00:00")

		self.assertEqual(client.calls[0]["filters"], {"modified": (">", "2020-01-01 00:00:00")})
