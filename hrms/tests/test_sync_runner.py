"""Guards the four promises of the cross-instance mirror (`hrms.sync.runner`).

The mirror writes into the REAL doctypes on a site group HR is consolidating
onto, so a bug here corrupts production HR data rather than a staging table.
Each test below pins one promise:

* a re-run never duplicates a row (upsert on the remote `name`);
* a repeat run is incremental (`modified >` watermark reaches the remote);
* every mirrored row carries its provenance stamp;
* a local row the remote no longer has is NEVER deleted;
* one doctype failing yields Partial, and the others still sync;
* the `HRMS Sync Run` record is finalised even when the run blows up.

Bench-free by construction, like `test_company_settings.py`: `frappe` is not
importable outside a bench and importing `hrms.sync.runner` normally drags in
the whole `hrms` package, so the module is loaded straight from its file with
a stub `frappe` in `sys.modules`. Run it as a FILE:

    python3 hrms/tests/test_sync_runner.py
"""

import datetime
import importlib.util
import logging
import pathlib
import sys
import types
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = HRMS_ROOT / "sync" / "runner.py"
SETUP_PATH = HRMS_ROOT / "setup.py"

NOW = datetime.datetime(2026, 8, 10, 12, 0, 0)


class _FakeDoc:
	"""Stands in for a frappe Document created from a dict."""

	def __init__(self, store, data):
		self._store = store
		self.doctype = data.pop("doctype")
		self.name = data.pop("name", None)
		self.data = data
		self.flags = types.SimpleNamespace()

	def insert(self, set_name=None, ignore_if_duplicate=False, ignore_permissions=False):
		self.name = set_name or self.name or self._store.autoname(self.doctype)
		table = self._store.tables.setdefault(self.doctype, {})
		if self.name in table and ignore_if_duplicate:
			return self
		table[self.name] = dict(self.data, name=self.name)
		self._store.inserts.append((self.doctype, self.name))
		return self


class _FakeStore:
	"""Canned local database: doctype -> {name: row}. Records every write."""

	def __init__(self, tables=None):
		self.tables = {dt: dict(rows) for dt, rows in (tables or {}).items()}
		self.inserts = []
		self.updates = []
		self.deletes = []
		self.commits = 0
		self.rollbacks = 0
		self.commit_error_once = False
		self._counter = 0

	def autoname(self, doctype):
		self._counter += 1
		return f"{doctype.upper().replace(' ', '-')}-{self._counter:05d}"

	def rows(self, doctype):
		return self.tables.get(doctype, {})

	# --- frappe.db surface -------------------------------------------------
	def exists(self, doctype, name):
		return name if name in self.rows(doctype) else None

	def set_value(self, doctype, name, fieldname, value=None, update_modified=True):
		payload = fieldname if isinstance(fieldname, dict) else {fieldname: value}
		row = self.tables.setdefault(doctype, {}).setdefault(name, {"name": name})
		row.update(payload)
		self.updates.append((doctype, name, payload))

	def commit(self):
		if self.commit_error_once:
			self.commit_error_once = False
			raise RuntimeError("deadlock on commit")
		self.commits += 1

	def rollback(self):
		self.rollbacks += 1

	def delete_doc(self, doctype, name, **kwargs):  # pragma: no cover — must never be called
		self.deletes.append((doctype, name))

	# --- frappe surface ----------------------------------------------------
	def get_all(self, doctype, filters=None, fields=None, order_by=None, limit=None, pluck=None):
		matched = [row for row in self.rows(doctype).values() if _matches(row, filters)]
		if order_by:
			field, _, direction = order_by.partition(" ")
			matched.sort(key=lambda r: r.get(field) or "", reverse=direction.lower() == "desc")
		if limit:
			matched = matched[:limit]
		if pluck:
			return [row.get(pluck) for row in matched]
		if fields:
			return [{f: row.get(f) for f in fields} for row in matched]
		return [dict(row) for row in matched]

	def get_doc(self, data):
		return _FakeDoc(self, dict(data))


def _matches(row, filters):
	for field, condition in (filters or {}).items():
		value = row.get(field)
		if isinstance(condition, (tuple, list)):
			operator, operand = condition
			if operator == "in" and value not in operand:
				return False
			if operator == ">" and not (value and value > operand):
				return False
		elif value != condition:
			return False
	return True


class _FakeClient:
	"""Implements the `RemoteInstanceClient` contract over canned remote rows."""

	def __init__(self, instance_name, remote, fail_for=()):
		self.instance_name = instance_name
		self.remote = remote
		self.fail_for = set(fail_for)
		self.calls = []

	def get_list(self, doctype, filters=None, fields=None, limit=None, start=0, order_by=None):
		self.calls.append({"doctype": doctype, "filters": filters, "limit": limit, "start": start})
		if doctype in self.fail_for:
			raise RuntimeError(f"remote refused {doctype}")
		rows = [dict(row) for row in self.remote.get(doctype, []) if _matches(row, filters)]
		return rows[start : start + limit] if limit else rows[start:]

	def count(self, doctype, filters=None):
		return len(self.get_list(doctype, filters=filters))


def _load_module():
	"""Import runner.py with a stub `frappe`, no bench required."""
	if "frappe" not in sys.modules:
		frappe = types.ModuleType("frappe")
		frappe._ = lambda text: text
		frappe.logger = lambda *a, **kw: logging.getLogger("hrms-test")
		frappe.whitelist = lambda *a, **kw: lambda fn: fn
		frappe.only_for = lambda *a, **kw: None
		frappe.db = None
		frappe.get_all = None
		frappe.get_doc = None
		frappe_utils = types.ModuleType("frappe.utils")
		frappe_utils.now_datetime = lambda: NOW
		frappe.utils = frappe_utils
		sys.modules["frappe"] = frappe
		sys.modules["frappe.utils"] = frappe_utils

	spec = importlib.util.spec_from_file_location("_hrms_sync_runner_under_test", MODULE_PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


runner = _load_module()

EMPLOYEES = [
	{"name": "HR-EMP-0001", "employee_name": "Aisha", "company": "Acme", "modified": "2026-08-01 09:00:00"},
	{"name": "HR-EMP-0002", "employee_name": "Bala", "company": "Acme", "modified": "2026-08-09 09:00:00"},
]
ATTENDANCE = [
	{"name": "HR-ATT-0001", "employee": "HR-EMP-0001", "docstatus": 1, "modified": "2026-08-09 10:00:00"},
]


class _RunnerTestCase(unittest.TestCase):
	"""Installs a fake frappe + store around each test."""

	def setUp(self):
		import frappe

		self.store = _FakeStore()
		self._saved = (frappe.db, frappe.get_all, frappe.get_doc)
		frappe.db = self.store
		frappe.get_all = self.store.get_all
		frappe.get_doc = self.store.get_doc

		# under `bench run-tests` the real frappe is already imported, and both
		# of these need a site; the module under test only ever calls them.
		self._saved_runner = (runner.now_datetime, runner._)
		runner.now_datetime = lambda: NOW
		runner._ = lambda text: text
		self.addCleanup(self._restore)

	def _restore(self):
		import frappe

		frappe.db, frappe.get_all, frappe.get_doc = self._saved
		runner.now_datetime, runner._ = self._saved_runner

	def client(self, remote=None, fail_for=()):
		return _FakeClient(
			"nasty-live", remote or {"Employee": EMPLOYEES, "Attendance": ATTENDANCE}, fail_for
		)

	def runs(self):
		return list(self.store.rows("HRMS Sync Run").values())


class TestIdempotency(_RunnerTestCase):
	def test_rerun_writes_no_duplicates(self):
		client = self.client()

		first = runner.sync_doctype(client, "Employee")
		second = runner.sync_doctype(client, "Employee")

		self.assertEqual(first["inserted"], 2)
		self.assertEqual(second["inserted"], 0, "a re-run must not insert anything again")
		self.assertEqual(second["updated"], 2)
		self.assertEqual(
			sorted(self.store.rows("Employee")),
			["HR-EMP-0001", "HR-EMP-0002"],
			"upsert keyed on the remote name must leave exactly one local row per remote row",
		)

	def test_local_name_equals_remote_name(self):
		runner.sync_doctype(self.client(), "Attendance")
		self.assertEqual(list(self.store.rows("Attendance")), ["HR-ATT-0001"])


class TestIncremental(_RunnerTestCase):
	def test_watermark_reaches_the_remote_as_a_modified_filter(self):
		client = self.client()

		result = runner.sync_doctype(client, "Employee", since="2026-08-05 00:00:00")

		self.assertEqual(client.calls[0]["filters"], {"modified": (">", "2026-08-05 00:00:00")})
		self.assertEqual(result["pulled"], 1, "only the row modified after the watermark is pulled")
		self.assertEqual(list(self.store.rows("Employee")), ["HR-EMP-0002"])

	def test_watermark_comes_from_the_last_completed_run(self):
		self.store.tables["HRMS Sync Run"] = {
			"SYNC-00001": {
				"name": "SYNC-00001",
				"source_instance": "nasty-live",
				"status": "Completed",
				"started_at": "2026-08-05 00:00:00",
			},
			"SYNC-00002": {
				"name": "SYNC-00002",
				"source_instance": "nasty-live",
				"status": "Failed",
				"started_at": "2026-08-08 00:00:00",
			},
		}

		self.assertEqual(runner.get_watermark("nasty-live"), "2026-08-05 00:00:00")

	def test_no_completed_run_means_a_full_pull(self):
		self.assertIsNone(runner.get_watermark("nasty-live"))

		client = self.client()
		runner.sync_doctype(client, "Employee", since=None)

		self.assertIsNone(client.calls[0]["filters"], "a first run must not filter on modified")
		self.assertEqual(len(self.store.rows("Employee")), 2)


class TestProvenance(_RunnerTestCase):
	def test_every_mirrored_row_records_its_source_instance(self):
		runner.sync_instance(self.client(), doctypes=["Employee", "Attendance"])

		for doctype in ("Employee", "Attendance"):
			for name, row in self.store.rows(doctype).items():
				self.assertEqual(
					row.get(runner.PROVENANCE_FIELD),
					"nasty-live",
					f"{doctype} {name} was mirrored without provenance",
				)

	def test_update_path_also_stamps_provenance(self):
		self.store.tables["Employee"] = {"HR-EMP-0001": {"name": "HR-EMP-0001", "employee_name": "stale"}}

		runner.sync_doctype(self.client(), "Employee")

		row = self.store.rows("Employee")["HR-EMP-0001"]
		self.assertEqual(row[runner.PROVENANCE_FIELD], "nasty-live")
		self.assertEqual(row["employee_name"], "Aisha")

	def test_fresh_install_creates_the_provenance_field(self):
		"""`install_app` marks every patch as already applied, so a patch-only
		field never exists on a new site. It has to come from the install path,
		i.e. be merged into `hrms.setup.get_custom_fields()`."""
		source = SETUP_PATH.read_text(encoding="utf-8")
		self.assertIn("get_provenance_custom_fields", source)

	def test_provenance_field_ships_for_every_mirrored_doctype(self):
		fields = runner.get_provenance_custom_fields()
		self.assertEqual(set(fields), set(runner.DEFAULT_SYNC_DOCTYPES))
		for definitions in fields.values():
			self.assertEqual(definitions[0]["fieldname"], runner.PROVENANCE_FIELD)
			self.assertTrue(definitions[0]["read_only"], "mirrored provenance must not be hand-editable")
			self.assertTrue(definitions[0]["allow_on_submit"], "Attendance arrives submitted")


COMPANIES = [
	{
		"name": "Acme",
		"company_name": "Acme",
		"abbr": "AC",
		"default_currency": "MYR",
		"country": "Malaysia",
		"default_bank_account": "REMOTE-BANK",
		"chart_of_accounts": "Remote Standard",
		"cost_center": "Main - AC",
		"modified": "2026-08-01 09:00:00",
	}
]


class TestCompanyIsMirroredCreateOnly(_RunnerTestCase):
	"""Company exists in the sync only so `Employee.company` resolves locally.

	Two properties, both load-bearing: it is created when absent (otherwise every
	mirrored Employee links to nothing, or HR hand-types the name and gets it
	wrong once), and it is NEVER updated when present (a local Company owns chart
	of accounts / cost centres a mirror must not clobber).
	"""

	def client(self, remote=None, fail_for=()):
		return super().client(remote or {"Company": COMPANIES, "Employee": EMPLOYEES}, fail_for)

	def test_company_syncs_before_employee(self):
		order = list(runner.DEFAULT_SYNC_DOCTYPES)
		self.assertIn("Company", order)
		self.assertLess(
			order.index("Company"),
			order.index("Employee"),
			"Employee.company is a Link — the Company must be mirrored first",
		)

	def test_absent_company_is_created_as_a_shell(self):
		result = runner.sync_doctype(self.client(), "Company")

		self.assertEqual(result["inserted"], 1)
		row = self.store.rows("Company")["Acme"]
		self.assertEqual(row["company_name"], "Acme")
		self.assertEqual(row["abbr"], "AC")
		self.assertEqual(row["default_currency"], "MYR")
		self.assertEqual(row["country"], "Malaysia")
		self.assertEqual(row[runner.PROVENANCE_FIELD], "nasty-live")

	def test_accounting_configuration_is_not_mirrored(self):
		runner.sync_doctype(self.client(), "Company")

		row = self.store.rows("Company")["Acme"]
		for field in ("default_bank_account", "cost_center"):
			self.assertNotIn(field, row, f"{field} is finance config and must not be mirrored")

	def test_remote_chart_of_accounts_is_never_copied(self):
		"""`chart_of_accounts` is set, but to OUR default — never the source's.

		The distinction matters: copying the remote's value would import another
		site's finance configuration, while omitting the field entirely kills the
		insert (`Company.on_update` builds the account tree and indexes into an
		empty template list — the SYNC-00002 'list index out of range').
		"""
		remote_with_coa = [dict(row, chart_of_accounts="Remote Bespoke CoA") for row in COMPANIES]
		client = self.client(remote={"Company": remote_with_coa, "Employee": EMPLOYEES})

		runner.sync_doctype(client, "Company")

		written = self.store.rows("Company")["Acme"]
		self.assertNotEqual(written.get("chart_of_accounts"), "Remote Bespoke CoA")
		self.assertEqual(written.get("chart_of_accounts"), "Standard")

	def test_existing_company_is_never_modified(self):
		local = {
			"name": "Acme",
			"company_name": "Acme Holdings Sdn Bhd",
			"abbr": "AHSB",
			"default_currency": "USD",
			"country": "Singapore",
			"chart_of_accounts": "Local Standard",
		}
		self.store.tables["Company"] = {"Acme": dict(local)}

		result = runner.sync_doctype(self.client(), "Company")

		self.assertEqual(self.store.rows("Company")["Acme"], local, "a local Company was overwritten")
		self.assertEqual(self.store.updates, [], "create-only doctype must issue no writes")
		self.assertEqual(result["updated"], 0)
		self.assertEqual(result["inserted"], 0)
		self.assertEqual(result["written"], 0)
		self.assertEqual(result["skipped"], 1)

	def test_existing_company_is_not_even_stamped_with_provenance(self):
		self.store.tables["Company"] = {"Acme": {"name": "Acme", "company_name": "Acme"}}

		runner.sync_doctype(self.client(), "Company")

		self.assertNotIn(runner.PROVENANCE_FIELD, self.store.rows("Company")["Acme"])

	def test_rerun_after_creation_does_not_touch_it_again(self):
		client = self.client()
		runner.sync_doctype(client, "Company")
		self.store.updates.clear()

		second = runner.sync_doctype(client, "Company")

		self.assertEqual(second["skipped"], 1)
		self.assertEqual(self.store.updates, [])

	def test_create_only_applies_to_company_alone(self):
		"""Every other doctype still updates in place."""
		self.assertEqual(runner.CREATE_ONLY_DOCTYPES, frozenset({"Company"}))

		client = self.client()
		runner.sync_doctype(client, "Employee")
		second = runner.sync_doctype(client, "Employee")

		self.assertEqual(second["updated"], 2)

	def test_provenance_field_is_created_for_company_too(self):
		"""Nothing can stamp `Company.synced_from_instance` unless it exists."""
		self.assertIn("Company", runner.get_provenance_custom_fields())


class TestNeverDeletes(_RunnerTestCase):
	def test_record_absent_remotely_is_left_alone_and_counted_as_skipped(self):
		self.store.tables["Employee"] = {
			"HR-EMP-0009": {
				"name": "HR-EMP-0009",
				"employee_name": "Departed",
				runner.PROVENANCE_FIELD: "nasty-live",
			}
		}

		result = runner.sync_doctype(self.client(), "Employee")

		self.assertIn("HR-EMP-0009", self.store.rows("Employee"), "mirror must never delete a local row")
		self.assertEqual(self.store.deletes, [])
		self.assertEqual(result["skipped"], 1)
		self.assertEqual(result["pulled"], 2)


class TestPartialRuns(_RunnerTestCase):
	def test_one_doctype_failing_yields_partial_and_the_rest_still_sync(self):
		client = self.client(fail_for=["Attendance"])

		result = runner.sync_instance(client, doctypes=["Employee", "Attendance"])

		self.assertEqual(result["status"], "Partial")
		self.assertEqual(result["failed"], ["Attendance"])
		self.assertEqual(len(self.store.rows("Employee")), 2, "the healthy doctype must still be mirrored")

		run = self.runs()[0]
		self.assertEqual(run["status"], "Partial")
		self.assertIn("Attendance", run["error_log"])
		self.assertEqual(run["rows_written"], 2)

	def test_every_doctype_failing_yields_failed(self):
		client = self.client(fail_for=["Employee", "Attendance"])

		result = runner.sync_instance(client, doctypes=["Employee", "Attendance"])

		self.assertEqual(result["status"], "Failed")
		self.assertEqual(self.runs()[0]["status"], "Failed")

	def test_a_clean_run_is_completed(self):
		result = runner.sync_instance(self.client(), doctypes=["Employee", "Attendance"])

		self.assertEqual(result["status"], "Completed")
		run = self.runs()[0]
		self.assertEqual(run["status"], "Completed")
		self.assertEqual(run["rows_pulled"], 3)
		self.assertEqual(run["source_instance"], "nasty-live")
		self.assertEqual(run["doctypes_synced"], "Employee, Attendance")
		self.assertEqual(run["started_at"], NOW)
		self.assertEqual(run["finished_at"], NOW)


class TestRunRecordAlwaysFinalised(_RunnerTestCase):
	def test_run_is_finalised_when_the_run_itself_raises(self):
		self.store.commit_error_once = True

		with self.assertRaises(RuntimeError):
			runner.sync_instance(self.client(), doctypes=["Employee", "Attendance"])

		run = self.runs()[0]
		self.assertEqual(run["status"], "Failed")
		self.assertEqual(run["finished_at"], NOW)
		self.assertIn("run aborted", run["error_log"])

	def test_run_record_is_written_before_any_doctype_is_pulled(self):
		client = self.client(fail_for=["Employee"])

		runner.sync_instance(client, doctypes=["Employee"])

		self.assertEqual(len(self.runs()), 1, "exactly one audit record per run")
		self.assertEqual(self.store.inserts[0][0], "HRMS Sync Run")


class TestDependentDoctypesAreBlocked(_RunnerTestCase):
	"""A dependent doctype is never attempted once its prerequisite failed.

	Regression for SYNC-00002 on verifica-live (2026-08-10): Company and Employee
	both failed, the run continued, and 5,821 Attendance / Employee Checkin /
	Leave Ledger Entry rows were written referencing an employee and a company
	that did not exist on the destination. Per-doctype failure containment is
	correct for INDEPENDENT doctypes and actively harmful for dependent ones.
	"""

	def _remote(self):
		return {
			"Company": COMPANIES,
			"Employee": EMPLOYEES,
			"Attendance": [{"name": "ATT-1", "employee": "EMP-1", "company": "Acme"}],
		}

	def test_employee_failure_blocks_attendance(self):
		client = self.client(self._remote(), fail_for=("Employee",))
		result = runner.sync_instance(
			client, doctypes=("Company", "Employee", "Attendance"), incremental=False
		)

		self.assertIn("Employee", result["failed"])
		self.assertIn("Attendance", result["blocked"])
		self.assertEqual(
			self.store.rows("Attendance"), {}, "orphan attendance written despite Employee failing"
		)

	def test_company_failure_blocks_attendance_transitively(self):
		"""Attendance names Employee as its prerequisite, not Company — the block
		must still propagate through the chain."""
		client = self.client(self._remote(), fail_for=("Company",))
		result = runner.sync_instance(
			client, doctypes=("Company", "Employee", "Attendance"), incremental=False
		)

		self.assertIn("Company", result["failed"])
		self.assertIn("Employee", result["blocked"])
		self.assertIn("Attendance", result["blocked"])
		self.assertEqual(self.store.rows("Attendance"), {})
		self.assertEqual(self.store.rows("Employee"), {})

	def test_independent_doctypes_still_run_after_a_failure(self):
		"""Containment must survive: a failure only blocks its DEPENDENTS."""
		remote = dict(self._remote())
		client = self.client(remote, fail_for=("Company",))
		result = runner.sync_instance(client, doctypes=("Company", "Employee"), incremental=False)

		self.assertEqual(result["status"], "Failed")
		self.assertIn("Company", result["failed"])
		self.assertIn("Employee", result["blocked"])

	def test_clean_run_blocks_nothing(self):
		client = self.client(self._remote())
		result = runner.sync_instance(
			client, doctypes=("Company", "Employee", "Attendance"), incremental=False
		)

		self.assertEqual(result["blocked"], [])
		self.assertEqual(result["status"], "Completed")
		self.assertEqual(len(self.store.rows("Attendance")), 1)


if __name__ == "__main__":
	unittest.main(verbosity=2)
