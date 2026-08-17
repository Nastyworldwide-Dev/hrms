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
from typing import ClassVar

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


class _FakeStoredDoc:
	"""An existing row loaded by (doctype, name); `save()` writes it back."""

	def __init__(self, store, doctype, name):
		self._store = store
		self.doctype = doctype
		self.name = name
		self.flags = types.SimpleNamespace()
		self.__dict__.update(store.rows(doctype).get(name, {}))

	def save(self, ignore_permissions=False):
		row = self._store.tables.setdefault(self.doctype, {}).setdefault(self.name, {"name": self.name})
		row.update({k: v for k, v in self.__dict__.items() if not k.startswith("_") and k != "flags"})
		self._store.updates.append((self.doctype, self.name, dict(row)))
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

	def get_value(self, doctype, name, fieldname=None, **kwargs):
		row = self.rows(doctype).get(name) if isinstance(name, str) else None
		if row is None:
			return None
		if isinstance(fieldname, list | tuple):
			return [row.get(f) for f in fieldname]
		return row.get(fieldname)

	def get_doc(self, data, name=None):
		"""Two shapes, both of which runner.py uses: a dict to insert, and
		(doctype, name) to load an existing row (the linked User)."""
		if name is not None:
			return _FakeStoredDoc(self, data, name)
		return _FakeDoc(self, dict(data))


def _matches(row, filters):
	for field, condition in (filters or {}).items():
		value = row.get(field)
		if isinstance(condition, tuple | list):
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
		self.calls.append(
			{
				"doctype": doctype,
				"filters": filters,
				"limit": limit,
				"start": start,
				"order_by": order_by,
			}
		)
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
		frappe.flags = types.SimpleNamespace()
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

	#: Parents the fixtures point at. Referential integrity is enforced per row,
	#: so a store without these writes nothing — mirroring the real destination,
	#: where a company must exist before its employees can land.
	SEED: ClassVar[dict] = {
		"Company": {"Acme": {"name": "Acme", "company_name": "Acme"}},
		"Employee": {
			"HR-EMP-0001": {"name": "HR-EMP-0001", "company": "Acme"},
			"HR-EMP-0002": {"name": "HR-EMP-0002", "company": "Acme"},
		},
	}

	#: Doctypes whose own rows the test asserts on; seeding those would pollute
	#: the counts, so each subclass drops what it is actually syncing.
	SEED_EXCLUDE: ClassVar[tuple] = ()

	def setUp(self):
		import frappe

		self.store = _FakeStore({dt: rows for dt, rows in self.SEED.items() if dt not in self.SEED_EXCLUDE})
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

	def seed_parent(self, doctype, name, **fields):
		"""Put a parent row in place for tests whose class excludes it from SEED."""
		self.store.tables.setdefault(doctype, {})[name] = dict(fields, name=name)

	def client(self, remote=None, fail_for=()):
		return _FakeClient(
			"nasty-live", remote or {"Employee": EMPLOYEES, "Attendance": ATTENDANCE}, fail_for
		)

	def runs(self):
		return list(self.store.rows("HRMS Sync Run").values())


class TestIdempotency(_RunnerTestCase):
	SEED_EXCLUDE = ("Employee",)

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
		self.seed_parent("Employee", "HR-EMP-0001", company="Acme")
		runner.sync_doctype(self.client(), "Attendance")
		self.assertEqual(list(self.store.rows("Attendance")), ["HR-ATT-0001"])


class TestIncremental(_RunnerTestCase):
	SEED_EXCLUDE = ("Employee",)

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
	SEED_EXCLUDE = ("Employee",)

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

	def test_provenance_field_ships_for_every_stamped_doctype(self):
		# STAMPED_DOCTYPES, not DEFAULT_SYNC_DOCTYPES: the latter now also carries
		# the create-only masters, which are HR-owned here and must stay unstamped.
		fields = runner.get_provenance_custom_fields()
		self.assertEqual(set(fields), set(runner.STAMPED_DOCTYPES))
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

	SEED_EXCLUDE = ("Company",)

	def client(self, remote=None, fail_for=()):
		return super().client(remote or {"Company": COMPANIES, "Employee": EMPLOYEES}, fail_for)

	def test_company_is_not_synced_automatically(self):
		"""Creating a Company means running ERPNext's setup, and on this version
		that path is broken two ways — "list index out of range" without
		`chart_of_accounts`, `'Company' object has no attribute
		'update_default_account'` with it. Both were hit on verifica-live. A human
		creates companies; the sync only reports which are missing."""
		self.assertNotIn("Company", runner.DEFAULT_SYNC_DOCTYPES)
		self.assertIn("Employee", runner.DEFAULT_SYNC_DOCTYPES)

	def test_employee_declares_company_as_a_row_dependency(self):
		"""Company is still a prerequisite — enforced per row instead."""
		self.assertEqual(runner.ROW_DEPENDENCIES["Employee"], {"company": "Company"})

	def test_absent_company_is_created_as_a_shell(self):
		result = runner.sync_doctype(self.client(), "Company")

		self.assertEqual(result["inserted"], 1)
		row = self.store.rows("Company")["Acme"]
		self.assertEqual(row["company_name"], "Acme")
		self.assertEqual(row["abbr"], "AC")
		self.assertEqual(row["default_currency"], "MYR")
		self.assertEqual(row["country"], "Malaysia")

	def test_a_company_shell_carries_no_provenance_stamp(self):
		"""It never really did — the stamp went into a field Company does not have.

		`get_provenance_custom_fields` has only ever created `synced_from_instance`
		on the four stamped doctypes, so the value the old payload set was dropped
		by `get_valid_dict` on the way to the database and survived only in this
		suite's fake store. Now the two ways a Company can be created here —
		`company_shells` and this path — agree: a Company on the hub is HR-owned
		and unstamped.
		"""
		runner.sync_doctype(self.client(), "Company")

		self.assertNotIn(runner.PROVENANCE_FIELD, self.store.rows("Company")["Acme"])

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

	def test_create_only_covers_company_and_every_master(self):
		"""Create-only means the local row always wins.

		Right for Company and right for the masters: HR tunes a Leave Type on this
		hub — the flags that drive balance arithmetic — and a mirror that reverted
		it to the source's copy on every run would be a silent data change nobody
		asked for. The stamped doctypes still update in place.
		"""
		self.seed_parent("Company", "Acme", company_name="Acme")
		self.assertEqual(runner.CREATE_ONLY_DOCTYPES, frozenset({"Company", *runner.MASTER_DOCTYPES}))
		for doctype in runner.STAMPED_DOCTYPES:
			self.assertNotIn(doctype, runner.CREATE_ONLY_DOCTYPES)

		client = self.client()
		runner.sync_doctype(client, "Employee")
		second = runner.sync_doctype(client, "Employee")

		self.assertEqual(second["updated"], 2)

	def test_provenance_covers_exactly_the_stamped_doctypes(self):
		"""Only the stamped doctypes need it, and every one of them has it —
		`parity.py` counts local rows by the stamp, so a gap here silently
		understates.

		Masters are deliberately excluded: they are HR-owned here, exactly like the
		Company shells, and stamping them would hand them to the write-block and
		lock HR out of their own masters.
		"""
		fields = runner.get_provenance_custom_fields()
		self.assertEqual(sorted(fields), sorted(runner.STAMPED_DOCTYPES))
		for master in runner.MASTER_DOCTYPES:
			self.assertNotIn(master, fields)


class TestMastersAreMirroredSoLinksResolve(_RunnerTestCase):
	"""Employee and Leave Ledger Entry link to masters that were never pulled.

	`_write_row` inserts with `ignore_links=True`, so a mirrored employee whose
	designation does not exist here lands pointing at nothing, and a ledger row
	whose leave type is absent produces a balance for a type the site cannot name.
	Nothing failed loudly; the data was simply wrong in a way only a person
	reading a report would notice.
	"""

	def test_masters_precede_the_rows_that_link_to_them(self):
		"""Tuple order IS sync order. Leave Type after Leave Ledger Entry would
		make the pull pointless on a first run."""
		order = list(runner.DEFAULT_SYNC_DOCTYPES)
		for master in runner.MASTER_DOCTYPES:
			self.assertIn(master, order)
		self.assertLess(order.index("Leave Type"), order.index("Leave Ledger Entry"))
		for master in runner.MASTER_DOCTYPES:
			self.assertLess(order.index(master), order.index("Employee"))

	def test_a_master_is_not_stamped_with_provenance(self):
		payload = runner._mirror_payload(
			{"name": "Annual Leave", "leave_type_name": "Annual Leave"}, "nasty-live", "Leave Type"
		)
		self.assertNotIn(runner.PROVENANCE_FIELD, payload)

	def test_a_stamped_doctype_still_carries_provenance(self):
		payload = runner._mirror_payload({"name": "HR-EMP-0001"}, "nasty-live", "Employee")
		self.assertEqual(payload[runner.PROVENANCE_FIELD], "nasty-live")

	def test_a_master_that_already_exists_locally_is_left_alone(self):
		self.seed_parent("Leave Type", "Annual Leave", leave_type_name="Annual Leave", max_leaves_allowed=20)
		client = self.client({"Leave Type": [{"name": "Annual Leave", "max_leaves_allowed": 5}]})

		result = runner.sync_doctype(client, "Leave Type")

		self.assertEqual(result["skipped"], 1)
		self.assertEqual(self.store.rows("Leave Type")["Annual Leave"]["max_leaves_allowed"], 20)

	def test_a_missing_master_never_blocks_an_employee(self):
		"""Designation is optional metadata. Skipping an employee because their
		designation has not landed would deny them the app over a job title."""
		self.assertNotIn("designation", runner.ROW_DEPENDENCIES.get("Employee", {}))
		self.assertNotIn("grade", runner.ROW_DEPENDENCIES.get("Employee", {}))

	def test_a_department_or_holiday_list_is_never_mirrored(self):
		"""Both would corrupt rather than merely dangle — Department is a NestedSet
		whose lft/rgt belong to the source's tree, and a Holiday List arrives
		without its holidays because /api/resource omits child tables."""
		self.assertNotIn("Department", runner.DEFAULT_SYNC_DOCTYPES)
		self.assertNotIn("Holiday List", runner.DEFAULT_SYNC_DOCTYPES)


class TestThePullIsScopedToTheServedCompanies(_RunnerTestCase):
	"""The `Companies Served` table said 7 of the source's 10 companies, and the
	runner pulled all 10 anyway: `sync_instance` never passed the `filters`
	argument `sync_doctype` has always accepted. Employees of three companies the
	hub was never meant to hold landed in it, and because every company existed
	locally nothing was even reported as skipped.
	"""

	SEED_EXCLUDE = ("Employee",)

	def register(self, *companies):
		for company in companies:
			self.store.tables.setdefault("HRMS ERP Instance Company", {})[f"row-{company}"] = {
				"name": f"row-{company}",
				"parent": "nasty-live",
				"company": company,
			}

	def test_only_the_served_companies_are_requested(self):
		self.register("Acme")
		self.seed_parent("Company", "Acme", company_name="Acme")
		self.seed_parent("Company", "Other", company_name="Other")
		remote = {
			"Employee": [
				*EMPLOYEES,
				{"name": "HR-EMP-9001", "company": "Other", "modified": "2026-08-09 09:00:00"},
			]
		}
		client = self.client(remote)

		runner.sync_instance(client, doctypes=["Employee"], incremental=False)

		employee_call = next(c for c in client.calls if c["doctype"] == "Employee")
		self.assertEqual(employee_call["filters"], {"company": ("in", ["Acme"])})
		self.assertNotIn("HR-EMP-9001", self.store.rows("Employee"))

	def test_an_unmapped_instance_still_pulls_everything(self):
		"""Backwards compatible on purpose: an instance whose table nobody has
		filled in must keep the behaviour it has today, not silently narrow to
		nothing."""
		self.seed_parent("Company", "Acme", company_name="Acme")
		client = self.client({"Employee": EMPLOYEES})

		runner.sync_instance(client, doctypes=["Employee"], incremental=False)

		employee_call = next(c for c in client.calls if c["doctype"] == "Employee")
		self.assertIsNone(employee_call["filters"])

	def test_employee_checkin_is_scoped_by_employee_because_it_has_no_company(self):
		"""Employee Checkin carries no `company` field, so the fence has to be the
		employees the Employee pass just mirrored — which is why Employee precedes
		it in the sync order."""
		self.register("Acme")
		self.seed_parent("Company", "Acme", company_name="Acme")
		self.store.tables.setdefault("Employee", {})["HR-EMP-0001"] = {
			"name": "HR-EMP-0001",
			"company": "Acme",
			runner.PROVENANCE_FIELD: "nasty-live",
		}

		scope = runner.scope_filter("Employee Checkin", ["Acme"], "nasty-live")

		self.assertEqual(scope, {"employee": ("in", ["HR-EMP-0001"])})

	def test_no_mirrored_employee_yet_asks_for_nothing_rather_than_everything(self):
		"""An empty allow-list must not degrade into "no filter" — that is how a
		scoped run quietly pulls the whole source."""
		scope = runner.scope_filter("Employee Checkin", ["Acme"], "nasty-live")

		self.assertIsNotNone(scope)
		self.assertEqual(scope["employee"][0], "in")
		self.assertNotIn("", scope["employee"][1])
		self.assertTrue(scope["employee"][1], "the sentinel must be non-empty so the remote gets a valid IN")

	def test_a_master_is_never_company_filtered(self):
		"""Leave Type has no company field; sending one would make the remote
		reject the read."""
		self.assertIsNone(runner.scope_filter("Leave Type", ["Acme"], "nasty-live"))


class TestNeverDeletes(_RunnerTestCase):
	SEED_EXCLUDE = ("Employee",)

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
	SEED_EXCLUDE = ("Employee",)

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
	SEED_EXCLUDE = ("Employee",)

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

	SEED_EXCLUDE = ("Company", "Employee")

	def _remote(self):
		return {
			"Company": COMPANIES,
			"Employee": EMPLOYEES,
			"Attendance": [{"name": "ATT-1", "employee": "HR-EMP-0001", "company": "Acme"}],
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


class TestParseDoctypes(unittest.TestCase):
	"""`doctypes` must accept what a human types, not only strict JSON.

	Requiring a JSON array meant pasting the documented URL into a browser lost
	the quotes and produced `JSONDecodeError: Expecting value: line 1 column 2` —
	a parser complaint that tells the caller nothing about what to send instead.
	"""

	def test_json_array(self):
		self.assertEqual(runner.parse_doctypes('["Company","Employee"]'), ("Company", "Employee"))

	def test_brackets_without_quotes(self):
		"""Exactly what a browser address bar produces."""
		self.assertEqual(runner.parse_doctypes("[Company,Employee]"), ("Company", "Employee"))

	def test_plain_comma_separated(self):
		self.assertEqual(runner.parse_doctypes("Company,Employee"), ("Company", "Employee"))

	def test_single_name(self):
		self.assertEqual(runner.parse_doctypes("Company"), ("Company",))

	def test_whitespace_and_single_quotes(self):
		self.assertEqual(runner.parse_doctypes(" Company , Employee "), ("Company", "Employee"))
		self.assertEqual(runner.parse_doctypes("['Company','Employee']"), ("Company", "Employee"))

	def test_empty_means_defaults(self):
		self.assertIsNone(runner.parse_doctypes(None))
		self.assertIsNone(runner.parse_doctypes(""))

	def test_sequence_passes_through(self):
		self.assertEqual(runner.parse_doctypes(["Company"]), ("Company",))


class TestRunSyncEndpointIsPostOnly(unittest.TestCase):
	"""SEC-03, same ruling as `company_shells.create_company_shells`.

	`run_sync` writes thousands of rows into the real doctypes. Reachable by GET,
	a logged-in HR Manager who loads a page carrying `<img src=".../run_sync?
	instance_name=...">` starts a full pull without ever clicking anything. The
	decorator is read from source rather than from the imported function because
	the bench-free stub replaces `frappe.whitelist` with a pass-through, so the
	kwargs never survive the import.
	"""

	def test_run_sync_is_post_only(self):
		import ast

		tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
		functions = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

		methods = []
		for decorator in functions["run_sync"].decorator_list:
			if isinstance(decorator, ast.Call):
				for keyword in decorator.keywords:
					if keyword.arg == "methods":
						methods = [element.value for element in keyword.value.elts]

		self.assertEqual(methods, ["POST"], "run_sync must be POST-only (SEC-03)")


class TestRowsWithMissingParentsAreNeverWritten(_RunnerTestCase):
	"""Referential integrity, enforced per row.

	Regression for SYNC-00003 on verifica-live (2026-08-10). Doctype-level gating
	was not enough: Company pulled 10 rows, errored on 9 and skipped 1, so it
	wrote NOTHING yet never raised — row-level error tolerance (added the same day
	to stop one bad Performance Band killing 5,000 good rows) swallowed every
	failure. Employee then ran against a green light and 266 employees landed
	pointing at companies that did not exist. The run reported "Completed".
	"""

	SEED_EXCLUDE = ("Company", "Employee")

	def test_employee_without_its_company_is_skipped_not_written(self):
		with self.assertRaises(RuntimeError):
			runner.sync_doctype(self.client({"Employee": EMPLOYEES}), "Employee")

		self.assertEqual(self.store.rows("Employee"), {}, "orphan employee written")

	def test_the_missing_parent_is_named(self):
		"""An operator has to know WHAT to create; a bare count is useless."""
		with self.assertRaises(RuntimeError) as caught:
			runner.sync_doctype(self.client({"Employee": EMPLOYEES}), "Employee")
		self.assertIn("Company: Acme", str(caught.exception))

	def test_writing_nothing_raises_so_dependents_stay_blocked(self):
		"""The precise hole in SYNC-00003: pulled>0, written==0, yet no raise."""
		client = self.client({"Employee": EMPLOYEES, "Attendance": ATTENDANCE})
		result = runner.sync_instance(client, doctypes=("Employee", "Attendance"), incremental=False)

		self.assertIn("Employee", result["failed"])
		self.assertIn("Attendance", result["blocked"])
		self.assertNotEqual(result["status"], "Completed")
		self.assertEqual(self.store.rows("Attendance"), {})

	def test_rows_with_parents_present_still_write(self):
		"""The check must not become a blanket refusal."""
		self.seed_parent("Company", "Acme", company_name="Acme")
		result = runner.sync_doctype(self.client({"Employee": EMPLOYEES}), "Employee")

		self.assertEqual(result["written"], 2)
		self.assertEqual(result["orphaned"], 0)


class TestLoginMappingIsHubOwned(_RunnerTestCase):
	"""`Employee.user_id` is this site's login mapping, not the source's.

	Mirroring it made a fixed login break again on the next pull: setting
	`user_id` on the hub survived only until the mirror put the source's value
	(usually empty) back, so the same person was locked out again days later and
	the per-user database fix looked like it had "stopped working".
	"""

	SEED_EXCLUDE = ("Employee",)

	def test_user_id_is_never_written_by_the_mirror(self):
		self.seed_parent("Company", "Acme", company_name="Acme")
		remote = [dict(EMPLOYEES[0], user_id="someone@source-erp.example")]

		runner.sync_doctype(self.client({"Employee": remote}), "Employee")

		self.assertNotIn("user_id", self.store.rows("Employee")["HR-EMP-0001"])

	def test_an_existing_local_link_survives_a_pull(self):
		self.seed_parent("Company", "Acme", company_name="Acme")
		self.seed_parent("Employee", "HR-EMP-0001", company="Acme", user_id="aisha@hub.example")
		remote = [dict(EMPLOYEES[0], user_id=None, employee_name="Aisha Renamed")]

		runner.sync_doctype(self.client({"Employee": remote}), "Employee")

		row = self.store.rows("Employee")["HR-EMP-0001"]
		self.assertEqual(row["user_id"], "aisha@hub.example", "the mirror clobbered the login mapping")
		self.assertEqual(row["employee_name"], "Aisha Renamed", "other fields must still mirror")


class TestUserStatusIsReconciled(_RunnerTestCase):
	"""`db.set_value` fires no doc events, so ERPNext's `update_user_status`
	never ran on a mirrored update and `User.enabled` drifted from
	`Employee.status` in both directions."""

	SEED_EXCLUDE = ("Employee",)

	def _sync(self, status):
		self.seed_parent("Company", "Acme", company_name="Acme")
		runner.sync_doctype(self.client({"Employee": [dict(EMPLOYEES[0], status=status)]}), "Employee")

	def test_a_left_employee_has_their_user_disabled(self):
		self.seed_parent("Employee", "HR-EMP-0001", company="Acme", user_id="aisha@hub.example")
		self.seed_parent("User", "aisha@hub.example", enabled=1)

		self._sync("Left")

		self.assertEqual(self.store.rows("User")["aisha@hub.example"]["enabled"], 0)

	def test_a_reactivated_employee_has_their_user_re_enabled(self):
		self.seed_parent("Employee", "HR-EMP-0001", company="Acme", user_id="aisha@hub.example")
		self.seed_parent("User", "aisha@hub.example", enabled=0)

		self._sync("Active")

		self.assertEqual(self.store.rows("User")["aisha@hub.example"]["enabled"], 1)

	def test_an_unlinked_employee_touches_no_user(self):
		self.seed_parent("Employee", "HR-EMP-0001", company="Acme")

		self._sync("Left")

		self.assertEqual(self.store.rows("User"), {})


class TestCheckpointNeverSkipsAnUnwrittenRow(_RunnerTestCase):
	"""A watermark may only advance past rows this site actually holds.

	The incident: an employee exists on Nasty ERP, the sync ran and reported
	Completed, and the employee is nevertheless absent here — permanently, because
	every later incremental run asks for `modified > <that run's start>` and the
	employee has not been touched on the source since.

	`sync_doctype` skips a row whose parent Company does not exist locally
	(referential integrity, SYNC-00003) and counts it as `orphaned`. It also counts
	a row that raised as `errored`. Neither counted towards `unfinished`, so the run
	was Completed, so `get_watermark` — which accepts only Completed runs — moved
	past rows that were never written.
	"""

	SEED_EXCLUDE = ("Employee",)

	REMOTE: ClassVar[list] = [
		{
			"name": "HR-EMP-0001",
			"employee_name": "Aisha",
			"company": "Acme",
			"modified": "2026-08-01 09:00:00",
		},
		{
			"name": "HR-EMP-0009",
			"employee_name": "Nadia",
			"company": "Nasty Sdn Bhd",
			"modified": "2026-08-02 09:00:00",
		},
	]

	def run_with_one_orphan(self):
		"""Acme exists locally; the second employee's company does not."""
		self.seed_parent("Company", "Acme", company_name="Acme")
		return runner.sync_instance(self.client({"Employee": self.REMOTE}), doctypes=["Employee"])

	def test_a_run_that_skipped_a_row_is_not_completed(self):
		result = self.run_with_one_orphan()

		self.assertEqual(result["written"], 1)
		self.assertEqual(result["orphaned"], 1)
		self.assertNotEqual(
			result["status"],
			"Completed",
			"a run that left a row unwritten reported Completed, so the watermark advanced past it",
		)

	def test_the_watermark_does_not_advance_past_a_skipped_row(self):
		self.run_with_one_orphan()

		self.assertIsNone(
			runner.get_watermark("nasty-live"),
			"the next incremental run will ask for modified > this run and never see the skipped employee",
		)

	def test_the_skipped_employee_is_still_reachable_after_the_company_arrives(self):
		"""The operator's actual repair path: create the missing company, re-run."""
		self.run_with_one_orphan()
		self.seed_parent("Company", "Nasty Sdn Bhd", company_name="Nasty Sdn Bhd")

		since = runner.get_watermark("nasty-live")
		result = runner.sync_doctype(self.client({"Employee": self.REMOTE}), "Employee", since=since)

		self.assertIn("HR-EMP-0009", self.store.rows("Employee"))
		self.assertEqual(result["orphaned"], 0)

	def test_an_errored_row_also_holds_the_watermark(self):
		self.seed_parent("Company", "Acme", company_name="Acme")
		remote = [
			dict(self.REMOTE[0]),
			{"name": "HR-EMP-0010", "company": "Acme", "modified": "2026-08-02 09:00:00", "bad": object()},
		]
		original = runner._write_row

		def explode(doctype, remote_name, payload):
			if remote_name == "HR-EMP-0010":
				raise RuntimeError("schema drift: unknown Select option")
			return original(doctype, remote_name, payload)

		runner._write_row = explode
		try:
			result = runner.sync_instance(self.client({"Employee": remote}), doctypes=["Employee"])
		finally:
			runner._write_row = original

		self.assertEqual(result["errored"], 1)
		self.assertNotEqual(result["status"], "Completed")
		self.assertIsNone(runner.get_watermark("nasty-live"))

	def test_a_clean_run_still_completes_and_advances(self):
		"""The guard must not make every run Partial."""
		self.seed_parent("Company", "Acme", company_name="Acme")
		result = runner.sync_instance(self.client({"Employee": EMPLOYEES}), doctypes=["Employee"])

		self.assertEqual(result["orphaned"], 0)
		self.assertEqual(result["errored"], 0)
		self.assertEqual(result["status"], "Completed")
		self.assertEqual(runner.get_watermark("nasty-live"), NOW)

	def test_legitimate_skips_do_not_hold_the_watermark(self):
		"""`skipped` conflates two things. A create-only doctype that already
		exists locally, and a local row the remote no longer returns, are both
		counted as skipped and neither is unfinished work."""
		self.seed_parent("Company", "Acme", company_name="Acme")
		self.seed_parent("Employee", "HR-EMP-9999", company="Acme", synced_from_instance="nasty-live")

		result = runner.sync_instance(self.client({"Employee": EMPLOYEES}), doctypes=["Employee"])

		self.assertGreaterEqual(result["skipped"], 1, "the local-only row should be counted as skipped")
		self.assertEqual(result["status"], "Completed")


class TestRunRecordShowsWhatWasNotWritten(_RunnerTestCase):
	"""An operator reading the run record has to be able to see that rows were
	left behind. Before this, `Completed` with `rows_skipped: 0` was the only
	visible outcome of a run that silently dropped an employee."""

	SEED_EXCLUDE = ("Employee",)

	def test_orphaned_and_errored_counts_are_recorded(self):
		self.seed_parent("Company", "Acme", company_name="Acme")
		runner.sync_instance(
			self.client({"Employee": TestCheckpointNeverSkipsAnUnwrittenRow.REMOTE}), doctypes=["Employee"]
		)

		run = self.runs()[0]
		self.assertEqual(run["rows_orphaned"], 1)
		self.assertEqual(run["rows_errored"], 0)
		self.assertEqual(run["status"], "Partial")

	def test_the_missing_parent_is_named_on_the_run(self):
		self.seed_parent("Company", "Acme", company_name="Acme")
		runner.sync_instance(
			self.client({"Employee": TestCheckpointNeverSkipsAnUnwrittenRow.REMOTE}), doctypes=["Employee"]
		)

		self.assertIn("Company: Nasty Sdn Bhd", self.runs()[0]["error_log"])


class TestPaginationIsDeterministic(_RunnerTestCase):
	"""Offset pagination over a non-unique sort key can skip rows.

	`modified asc` alone leaves ties unordered, and a bulk update on the source
	gives thousands of employees the same `modified` to the second. If the remote
	returns those ties in a different order between page 1 and page 2 — which it
	is entitled to do — a row at the boundary is never returned to us at all.
	"""

	SEED_EXCLUDE = ("Employee",)

	def test_the_sort_key_is_unique(self):
		self.seed_parent("Company", "Acme", company_name="Acme")
		client = self.client()

		runner.sync_doctype(client, "Employee")

		order_by = client.calls[0]["order_by"]
		self.assertIn("modified", order_by)
		self.assertIn("name", order_by, "ties on `modified` must break on the unique key")


class TestTheRunnerWalksEveryPage(_RunnerTestCase):
	"""The runner keeps its own offset loop on top of the client's paging.

	`sync_doctype` stops when a page comes back shorter than `page_size`, so a
	remote holding exactly one full page plus one row must still yield that last
	row — otherwise the employee at position 501 is invisible.
	"""

	SEED_EXCLUDE = ("Employee",)

	def remote(self, count):
		return [
			{
				"name": f"HR-EMP-{i:04d}",
				"employee_name": f"Staff {i}",
				"company": "Acme",
				"modified": f"2026-08-01 09:00:{i % 60:02d}",
			}
			for i in range(1, count + 1)
		]

	def test_a_row_past_the_first_page_still_lands(self):
		self.seed_parent("Company", "Acme", company_name="Acme")
		rows = self.remote(5)

		result = runner.sync_doctype(self.client({"Employee": rows}), "Employee", page_size=2)

		self.assertEqual(result["pulled"], 5)
		self.assertEqual(result["written"], 5)
		self.assertIn("HR-EMP-0005", self.store.rows("Employee"))

	def test_every_page_asks_for_the_same_total_order(self):
		self.seed_parent("Company", "Acme", company_name="Acme")
		client = self.client({"Employee": self.remote(5)})

		runner.sync_doctype(client, "Employee", page_size=2)

		self.assertGreater(len(client.calls), 1, "the fixture must span more than one page")
		self.assertEqual({call["order_by"] for call in client.calls}, {runner.PAGE_ORDER})
		self.assertEqual([call["start"] for call in client.calls], [0, 2, 4])


class TestMalformedSourceRows(_RunnerTestCase):
	SEED_EXCLUDE = ("Employee",)

	def test_a_row_without_a_name_is_skipped_not_guessed_at(self):
		"""The remote `name` is the upsert key. A row without one cannot be
		written idempotently, so inventing a name would create a duplicate on
		every future run."""
		self.seed_parent("Company", "Acme", company_name="Acme")
		rows = [dict(EMPLOYEES[0]), {"employee_name": "Nameless", "company": "Acme"}]

		result = runner.sync_doctype(self.client({"Employee": rows}), "Employee")

		self.assertEqual(result["written"], 1)
		self.assertEqual(result["skipped"], 1)
		self.assertEqual(list(self.store.rows("Employee")), ["HR-EMP-0001"])

	def test_a_duplicate_source_identifier_yields_one_local_row(self):
		"""Two remote rows sharing a `name` are the same record seen twice, and
		the upsert has to collapse them rather than double-write."""
		self.seed_parent("Company", "Acme", company_name="Acme")
		rows = [dict(EMPLOYEES[0]), dict(EMPLOYEES[0], employee_name="Aisha Renamed")]

		result = runner.sync_doctype(self.client({"Employee": rows}), "Employee")

		self.assertEqual(result["pulled"], 2)
		self.assertEqual(len(self.store.rows("Employee")), 1)
		self.assertEqual(self.store.rows("Employee")["HR-EMP-0001"]["employee_name"], "Aisha Renamed")


if __name__ == "__main__":
	unittest.main(verbosity=2)
