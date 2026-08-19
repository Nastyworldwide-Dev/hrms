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
		self.commit_error_after = 0
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
		for key, item in payload.items():
			# Faithful to MariaDB: a python list in a SET clause is SQL error
			# 1064 — SYNC-00074 failed all 20 Appraisal updates exactly here.
			# The store used to accept lists silently, which is why the
			# harness never caught it.
			if isinstance(item, list | dict):
				raise Exception(f"(1064, \"You have an error in your SQL syntax near '{item!r}'\") [{key}]")
		row = self.tables.setdefault(doctype, {}).setdefault(name, {"name": name})
		row.update(payload)
		self.updates.append((doctype, name, payload))

	def delete(self, doctype, filters=None):
		# frappe.db.delete — used ONLY for child-table replacement on a
		# mirrored UPDATE. Parent rows are still never deleted (delete_doc
		# below stays the must-never-be-called probe).
		table = self.tables.get(doctype, {})
		for name in [n for n, row in table.items() if _matches(row, filters)]:
			table.pop(name)
		self.child_deletes = getattr(self, "child_deletes", [])
		self.child_deletes.append((doctype, dict(filters or {})))

	def commit(self):
		# `commit_error_after` lets a test aim the failure past the run record's own
		# commit — `_start_run` makes that one durable before any doctype is pulled.
		if self.commit_error_once and self.commits >= self.commit_error_after:
			self.commit_error_once = False
			raise RuntimeError("deadlock on commit")
		self.commits += 1

	def rollback(self, save_point=None):
		# save_point arrived with the per-row isolation fix (7376d8fc0): a named
		# rollback undoes ONE row, a bare one undoes the pass. This store applies
		# writes immediately, so the semantic the runner tests actually rely on —
		# "a failed row does not destroy its predecessors" — holds by construction;
		# the counter records which flavour was asked for.
		if save_point is None:
			self.rollbacks += 1
		else:
			self.savepoint_rollbacks = getattr(self, "savepoint_rollbacks", 0) + 1

	def savepoint(self, name):
		self.savepoints = getattr(self, "savepoints", 0) + 1

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


def runner_absent_error(doctype):
	"""The shape `RemoteInstanceClient` raises when the source has no such doctype."""
	error = RuntimeError(f"remote rejected the read (status=404, endpoint=/api/resource/{doctype})")
	error.status_code = 404
	return error


#: What THIS site's Employee can store, for the schema-narrowing tests. Only
#: Employee is described: `_local_schema` raises for anything else, which makes
#: the narrowing fail open and leaves every other test's payload untouched —
#: exactly the production behaviour when meta cannot be read.
FAKE_EMPLOYEE_COLUMNS = {
	"name",
	"employee_name",
	"company",
	"status",
	"user_id",
	"company_email",
	"department",
	"designation",
	"branch",
	"grade",
	"holiday_list",
	"reports_to",
	"performance_band",
	"docstatus",
	"synced_from_instance",
}

FAKE_EMPLOYEE_SELECTS = {"performance_band": {"", "B", "B2", "C", "D", "E1", "E2", "F"}}


#: A child-table doctype, so the narrowing can be shown to keep its children.
#: `holidays` is deliberately NOT a column — that is the whole point.
FAKE_HOLIDAY_LIST_COLUMNS = {"name", "holiday_list_name", "from_date", "to_date"}
FAKE_HOLIDAY_LIST_TABLES = {"holidays"}


#: A SUBMITTABLE doctype whose `on_submit` writes into another mirrored doctype —
#: the shape the lifecycle rule exists for.
FAKE_LEAVE_ALLOCATION_COLUMNS = {
	"name",
	"employee",
	"leave_type",
	"from_date",
	"to_date",
	"new_leaves_allocated",
	"docstatus",
	"synced_from_instance",
}


def _fake_local_schema(doctype):
	if doctype == "Employee":
		return set(FAKE_EMPLOYEE_COLUMNS), dict(FAKE_EMPLOYEE_SELECTS)
	if doctype == "Holiday List":
		return set(FAKE_HOLIDAY_LIST_COLUMNS) | set(FAKE_HOLIDAY_LIST_TABLES), {}
	if doctype == "Leave Allocation":
		return set(FAKE_LEAVE_ALLOCATION_COLUMNS), {}
	raise RuntimeError(f"no meta for {doctype} in this harness")


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
		self._saved = (frappe.db, frappe.get_all, frappe.get_doc, getattr(frappe, "session", None))
		frappe.session = types.SimpleNamespace(user="hr@example.com")
		frappe.db = self.store
		frappe.get_all = self.store.get_all
		frappe.get_doc = self.store.get_doc

		# under `bench run-tests` the real frappe is already imported, and both
		# of these need a site; the module under test only ever calls them.
		self._saved_schema = runner._local_schema
		runner._local_schema = _fake_local_schema
		self.addCleanup(setattr, runner, "_local_schema", self._saved_schema)
		# The company fence (3fe9d6f03) resolves the session user's User
		# Permissions — a table this store does not describe. The harness runs
		# UNFENCED, which is the single-company default; the fence's own
		# behaviour has its own tests.
		self._saved_fence = runner.require_unfenced
		runner.require_unfenced = lambda *a, **k: None
		self.addCleanup(setattr, runner, "require_unfenced", self._saved_fence)

		self._saved_runner = (runner.now_datetime, runner._)
		runner.now_datetime = lambda: NOW
		runner._ = lambda text: text
		self.addCleanup(self._restore)

	def _restore(self):
		import frappe

		frappe.db, frappe.get_all, frappe.get_doc, frappe.session = self._saved
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

	def test_department_is_mirrored_without_the_sources_tree_arithmetic(self):
		"""Department was excluded because mirroring it would CORRUPT rather than
		merely dangle: it is a NestedSet, and `lft`/`rgt` describe a position in the
		SOURCE's tree.

		That reason was right about the arithmetic and wrong about the doctype.
		Excluding it left 289 employees pointing at departments this site does not
		have, and cost department-based approver routing entirely. The positions are
		dropped and recomputed here; the shape is mirrored.

		Holiday List was once excluded alongside it for a weaker reason — the list
		endpoint cannot see a child table — which was a limit of how we were reading,
		not of what could safely be written. `client.get_doc` removed it, and it is
		what lets Department bring its approver tables across too.
		"""
		self.assertIn("Department", runner.DEFAULT_SYNC_DOCTYPES)
		self.assertEqual(runner.LOCALLY_OWNED_FIELDS["Department"], ("lft", "rgt", "old_parent"))


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
		# Past the run record's own commit: this test is about a failure DURING the
		# pull, not about failing to record that a pull began.
		self.store.commit_error_after = 1

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


class TestChildTablesArriveWithTheirParent(_RunnerTestCase):
	"""A Holiday List with no holidays in it is worse than no Holiday List.

	`get_list` returns parent columns only, so a calendar mirrored through it
	arrives looking complete and empty exactly where it counts — and an empty
	calendar does not raise. It silently counts every weekend and public holiday
	as a working day, in leave arithmetic and in attendance alike.

	These doctypes are therefore re-read one at a time through the single-document
	endpoint. They are low-cardinality policy records — a handful of calendars and
	shift patterns per company — so N+1 requests is the cheap half of the trade.
	"""

	SEED_EXCLUDE = ("Employee",)

	REMOTE_LIST: ClassVar[list] = [{"name": "2026 MY", "modified": "2026-08-01 09:00:00"}]
	FULL_DOC: ClassVar[dict] = {
		"name": "2026 MY",
		"holiday_list_name": "2026 MY",
		"from_date": "2026-01-01",
		"to_date": "2026-12-31",
		"holidays": [{"holiday_date": "2026-01-01", "description": "New Year"}],
	}

	def client(self, remote=None, fail_for=()):
		client = super().client(remote or {"Holiday List": self.REMOTE_LIST}, fail_for)
		client.docs = {("Holiday List", "2026 MY"): dict(self.FULL_DOC)}
		client.doc_calls = []

		def get_doc(doctype, name):
			client.doc_calls.append((doctype, name))
			return dict(client.docs.get((doctype, name), {}))

		client.get_doc = get_doc
		return client

	def test_the_full_document_is_fetched_for_a_child_table_doctype(self):
		client = self.client()

		runner.sync_doctype(client, "Holiday List")

		self.assertEqual(client.doc_calls, [("Holiday List", "2026 MY")])

	def test_the_child_rows_are_written(self):
		runner.sync_doctype(self.client(), "Holiday List")

		row = self.store.rows("Holiday List")["2026 MY"]
		self.assertEqual(len(row["holidays"]), 1)
		self.assertEqual(row["holidays"][0]["holiday_date"], "2026-01-01")

	def test_source_bookkeeping_is_stripped_from_child_rows(self):
		"""A child row carrying the source's `name`/`parent` would be inserted under
		another instance's identifiers and belong to nothing here."""
		payload = runner._mirror_payload(
			{
				"name": "2026 MY",
				"holidays": [
					{
						"name": "abc123",
						"parent": "2026 MY",
						"parenttype": "Holiday List",
						"owner": "someone@source",
						"creation": "2020-01-01",
						"docstatus": 0,
						"idx": 1,
						"holiday_date": "2026-01-01",
					}
				],
			},
			"nasty-live",
			"Holiday List",
		)

		child = payload["holidays"][0]
		self.assertEqual(child["holiday_date"], "2026-01-01")
		# `idx` goes too: Frappe numbers children from the list order on insert, and
		# the source's numbering would only be authoritative until a row is dropped.
		for stripped in ("name", "parent", "parenttype", "owner", "creation", "docstatus", "idx"):
			self.assertNotIn(stripped, child)

	def test_child_row_order_is_preserved(self):
		"""Ordering has to come from somewhere once `idx` is stripped — the list."""
		payload = runner._mirror_payload(
			{
				"name": "2026 MY",
				"holidays": [
					{"idx": 1, "holiday_date": "2026-01-01"},
					{"idx": 2, "holiday_date": "2026-02-01"},
				],
			},
			"nasty-live",
			"Holiday List",
		)

		self.assertEqual(
			[child["holiday_date"] for child in payload["holidays"]], ["2026-01-01", "2026-02-01"]
		)

	def test_a_doctype_without_child_tables_is_never_re_fetched(self):
		"""N+1 is paid only where a child table makes it necessary."""
		self.seed_parent("Company", "Acme", company_name="Acme")
		client = self.client({"Employee": EMPLOYEES})
		client.docs = {}

		runner.sync_doctype(client, "Employee")

		self.assertEqual(client.doc_calls, [])

	def test_every_child_table_doctype_is_actually_mirrored(self):
		"""A doctype listed for the expensive path but never pulled is dead config."""
		for doctype in runner.CHILD_TABLE_DOCTYPES:
			self.assertIn(doctype, runner.DEFAULT_SYNC_DOCTYPES)


class TestChildTablesSurviveAnUpdate(_RunnerTestCase):
	"""SYNC-00074, 2026-08-19: every one of 20 Appraisal UPDATEs died with SQL
	1064. `db.set_value` builds a SET clause from whatever it is handed, and
	the payload of a doctype in CHILD_TABLE_DOCTYPES carries LISTS. Masters
	never reach the update branch — create-only rows are skipped once present
	— so Appraisal, the first STAMPED doctype with load-bearing child tables,
	was the first write in the mirror's life to take that path. The update
	branch must strip children out of `set_value` and replace the child rows
	hook-free instead; the store's `set_value` now refuses lists exactly like
	MariaDB, so this class cannot quietly regress.
	"""

	KRA_ROWS: ClassVar[list] = [
		{"kra": "Sales Achievement vs Target", "score": 4},
		{"kra": "Device Deployment", "score": 3},
	]

	def setUp(self):
		super().setUp()
		import frappe

		def schema(doctype):
			if doctype == "Appraisal":
				return {
					"name",
					"employee",
					"company",
					"docstatus",
					"synced_from_instance",
					"appraisal_kra",
				}, {}
			return _fake_local_schema(doctype)

		runner._local_schema = schema

		if hasattr(runner, "_child_table_map"):
			self._saved_map = runner._child_table_map
			runner._child_table_map = lambda doctype: {"appraisal_kra": "Appraisal KRA"}
			self.addCleanup(setattr, runner, "_child_table_map", self._saved_map)

		store = self.store

		class _NewChild:
			def __init__(self, doctype):
				self.doctype = doctype
				self.flags = types.SimpleNamespace()

			def update(self, values):
				self.__dict__.update(values)

			def db_insert(self):
				row = {k: v for k, v in self.__dict__.items() if not k.startswith("_") and k != "flags"}
				store.tables.setdefault(self.doctype, {})[self.name] = row
				store.inserts.append((self.doctype, self.name))

		self._counter = [0]

		def fake_hash(length=10):
			self._counter[0] += 1
			return f"child{self._counter[0]:04d}"

		self._saved_frappe = (getattr(frappe, "new_doc", None), getattr(frappe, "generate_hash", None))
		frappe.new_doc = _NewChild
		frappe.generate_hash = fake_hash
		self.addCleanup(self._restore_frappe)

	def _restore_frappe(self):
		import frappe

		frappe.new_doc, frappe.generate_hash = self._saved_frappe

	def _update_existing(self, docstatus=1):
		runner._write_row.dropped_fields = {}
		self.seed_parent(
			"Appraisal",
			"HR-APR-2026-00011",
			employee="HR-EMP-0001",
			docstatus=docstatus,
			appraisal_kra="stale-marker",
		)
		return runner._write_row(
			"Appraisal",
			"HR-APR-2026-00011",
			{
				"employee": "HR-EMP-0001",
				"docstatus": docstatus,
				"appraisal_kra": [dict(row) for row in self.KRA_ROWS],
			},
		)

	def test_an_update_with_children_writes_instead_of_raising_1064(self):
		self.assertEqual(self._update_existing(), "updated")
		for _doctype, _name, payload in self.store.updates:
			for value in payload.values():
				self.assertNotIsInstance(value, list, "a list reached db.set_value — SQL 1064")

	def test_children_are_replaced_not_appended(self):
		self._update_existing()
		self.assertIn(
			(
				"Appraisal KRA",
				{"parent": "HR-APR-2026-00011", "parenttype": "Appraisal", "parentfield": "appraisal_kra"},
			),
			getattr(self.store, "child_deletes", []),
			"old child rows must be deleted before the source's are written",
		)
		rows = list(self.store.rows("Appraisal KRA").values())
		self.assertEqual(len(rows), 2)
		self.assertEqual([row["idx"] for row in rows], [1, 2], "order comes from the list")
		for row in rows:
			self.assertEqual(row["parent"], "HR-APR-2026-00011")
			self.assertEqual(row["parentfield"], "appraisal_kra")

	def test_replaced_children_carry_the_parents_docstatus(self):
		"""The insert path leaves children at 0 under a submitted parent (a
		known cosmetic wart); the replacement path should at least not add a
		second inconsistency of its own."""
		self._update_existing(docstatus=1)
		for row in self.store.rows("Appraisal KRA").values():
			self.assertEqual(row["docstatus"], 1)

	def test_the_flat_fields_still_reach_set_value(self):
		self._update_existing()
		flats = [p for d, n, p in self.store.updates if d == "Appraisal"]
		self.assertTrue(any("employee" in p for p in flats), "flat fields must still be updated")


class TestTheHubCanRunHrOnItsOwn(_RunnerTestCase):
	"""What an employee record needs before HR can be done here rather than on the
	source ERP.

	The gap this closes: leave application THREW on the hub — `get_holidays` ->
	`get_holiday_dates_between_range` defaults to `raise_exception=True`, and no
	`Holiday List Assignment` existed for any mirrored employee or their company.
	Roster and charts pass `raise_exception=False` and so returned no holidays at
	all, silently. Shift planning had nothing to plan with.
	"""

	def test_holiday_calendars_are_mirrored(self):
		"""The calendar comes over; the ASSIGNMENT is derived from it plus the
		employee — see TestHolidayAssignmentsAreDerivedNotMirrored."""
		self.assertIn("Holiday List", runner.DEFAULT_SYNC_DOCTYPES)

	def test_shift_planning_is_mirrored(self):
		for doctype in ("Shift Type", "Shift Schedule", "Shift Schedule Assignment", "Shift Assignment"):
			self.assertIn(doctype, runner.DEFAULT_SYNC_DOCTYPES)

	def test_policy_records_are_hr_owned_and_operational_rows_are_not(self):
		"""The authority split. A calendar or a shift pattern is policy: seeded once,
		then owned here, so an HR edit survives every later run. A per-employee
		assignment is operational: stamped, and superseded by adding a newer record
		rather than by mutating a mirrored one — which is what keeps provenance and
		parity honest.
		"""
		for policy in ("Holiday List", "Shift Type", "Shift Schedule"):
			self.assertIn(policy, runner.CREATE_ONLY_DOCTYPES)
		for operational in ("Shift Assignment", "Shift Schedule Assignment"):
			self.assertIn(operational, runner.STAMPED_DOCTYPES)
			self.assertNotIn(operational, runner.CREATE_ONLY_DOCTYPES)

	def test_an_hr_edit_to_a_mirrored_calendar_survives_the_next_run(self):
		"""The whole point of create-only for policy: HR changes a holiday here and
		the mirror does not quietly put the source's version back."""
		self.seed_parent("Holiday List", "2026 MY", holiday_list_name="2026 MY", to_date="2026-12-30")
		client = self.client({"Holiday List": [{"name": "2026 MY", "to_date": "2026-12-31"}]})
		client.get_doc = lambda doctype, name: {"name": "2026 MY", "to_date": "2026-12-31"}

		result = runner.sync_doctype(client, "Holiday List")

		self.assertEqual(result["skipped"], 1)
		self.assertEqual(self.store.rows("Holiday List")["2026 MY"]["to_date"], "2026-12-30")

	def test_shift_rows_declare_their_parents(self):
		"""A shift assignment whose employee or shift type never landed would point
		at nothing; `ignore_links=True` means nothing objects at write time."""
		self.assertEqual(
			runner.ROW_DEPENDENCIES["Shift Assignment"],
			{"employee": "Employee", "shift_type": "Shift Type"},
		)
		self.assertEqual(
			runner.ROW_DEPENDENCIES["Shift Schedule Assignment"],
			{"employee": "Employee", "shift_schedule": "Shift Schedule"},
		)

	def test_masters_precede_the_assignments_that_point_at_them(self):
		order = list(runner.DEFAULT_SYNC_DOCTYPES)
		self.assertLess(order.index("Shift Type"), order.index("Shift Assignment"))
		self.assertLess(order.index("Shift Schedule"), order.index("Shift Schedule Assignment"))
		self.assertLess(order.index("Employee"), order.index("Shift Assignment"))

	def test_shift_rows_are_scoped_to_the_served_companies(self):
		"""Both carry `company`, so neither needs the employee-list fallback."""
		for doctype in ("Shift Assignment", "Shift Schedule Assignment"):
			self.assertEqual(
				runner.scope_filter(doctype, ["Acme"], "nasty-live"), {"company": ("in", ["Acme"])}
			)


class TestADoctypeTheSourceDoesNotHave(_RunnerTestCase):
	"""A version gap is not a failure, and must not behave like one.

	verifica-live, 2026-08-17: `Holiday List Assignment` returned 403, then 404
	once permissions were bypassed. The source runs an HRMS predating that doctype,
	so it simply is not there. (403 first because `has_permission` on an unknown
	doctype is False for anyone who is not System Manager; bypass that and the
	existence check answers instead.)

	Treated as a failure it is permanent: every run degrades to Partial, and since
	`Completed` requires nothing outstanding, the watermark never advances and the
	cutover gate can never authorise. The mirror has to be able to say "that source
	does not have this" and carry on — there is no outstanding work to come back
	for.
	"""

	SEED_EXCLUDE = ("Employee",)

	def absent_client(self, doctype="Leave Type"):
		client = self.client({"Employee": EMPLOYEES})
		real = client.get_list

		def get_list(dt, **kwargs):
			if dt == doctype:
				raise runner_absent_error(dt)
			return real(dt, **kwargs)

		client.get_list = get_list
		return client

	def test_an_absent_doctype_does_not_fail_the_run(self):
		self.seed_parent("Company", "Acme", company_name="Acme")

		result = runner.sync_instance(
			self.absent_client(),
			doctypes=["Employee", "Leave Type"],
			incremental=False,
		)

		self.assertEqual(result["status"], "Completed")
		self.assertIn("Leave Type", result["absent"])
		self.assertNotIn("Leave Type", result["failed"])

	def test_the_run_record_says_which_doctype_the_source_lacks(self):
		self.seed_parent("Company", "Acme", company_name="Acme")

		runner.sync_instance(self.absent_client(), doctypes=["Employee", "Leave Type"], incremental=False)

		log = self.runs()[0]["error_log"]
		self.assertIn("Leave Type", log)
		self.assertIn("not present", log.lower())

	def test_the_rest_of_the_run_still_writes(self):
		"""The whole point — one version gap must not cost the other thirteen."""
		self.seed_parent("Company", "Acme", company_name="Acme")

		runner.sync_instance(self.absent_client(), doctypes=["Employee", "Leave Type"], incremental=False)

		self.assertEqual(len(self.store.rows("Employee")), 2)

	def test_a_real_remote_failure_is_still_a_failure(self):
		"""404 means "not there". Anything else still degrades the run — a 500 or a
		dropped connection is outstanding work, and must hold the watermark."""
		self.seed_parent("Company", "Acme", company_name="Acme")
		client = self.client({"Employee": EMPLOYEES}, fail_for=["Attendance"])

		result = runner.sync_instance(client, doctypes=["Employee", "Attendance"], incremental=False)

		self.assertEqual(result["status"], "Partial")
		self.assertIn("Attendance", result["failed"])


class TestTheMastersThatCarryFunction(_RunnerTestCase):
	"""Two of the senior's own doctypes were referenced by mirrored rows and never
	brought across, so the features they drive were inert on the hub.

	A link scan over every mirrored doctype found 21 targets the mirror does not
	carry. Most are correctly absent — `User` is hub-owned, payroll is a separate
	decision, request documents stay on the source. Two were not:

	* `Overtime Type` — referenced by Shift Type, Attendance, Employee Checkin AND
	  Shift Assignment. Without it, overtime rates resolve to nothing and the
	  Replacement Leave bank the PWA shows has no rule behind it.
	* `Shift Location` — carries a `shift_rules` child table described on the
	  Employee form as "drives the automatic Shift Assignment rules". Employees
	  arrived with `shift_location` set to a record that does not exist here, so
	  the rules had nothing to run.

	Both are flat, unsubmittable and free of lifecycle hooks, so they mirror as
	create-only masters exactly like Holiday List — HR owns them here once seeded.
	"""

	def test_both_are_mirrored(self):
		for doctype in ("Overtime Type", "Shift Location"):
			self.assertIn(doctype, runner.DEFAULT_SYNC_DOCTYPES)
			self.assertIn(doctype, runner.MASTER_DOCTYPES)

	def test_they_precede_everything_that_links_to_them(self):
		order = list(runner.DEFAULT_SYNC_DOCTYPES)
		for dependent in ("Shift Type", "Employee", "Attendance", "Employee Checkin", "Shift Assignment"):
			self.assertLess(order.index("Overtime Type"), order.index(dependent))
		for dependent in ("Employee", "Shift Schedule Assignment", "Shift Assignment"):
			self.assertLess(order.index("Shift Location"), order.index(dependent))

	def test_shift_location_brings_its_rules(self):
		"""`shift_rules` is the whole point — a Shift Location without them is a
		label, and automatic shift assignment has nothing to act on."""
		self.assertIn("Shift Location", runner.CHILD_TABLE_DOCTYPES)

	def test_overtime_type_brings_its_components(self):
		self.assertIn("Overtime Type", runner.CHILD_TABLE_DOCTYPES)

	def test_they_are_hr_owned_once_seeded(self):
		for doctype in ("Overtime Type", "Shift Location"):
			self.assertIn(doctype, runner.CREATE_ONLY_DOCTYPES)
			self.assertNotIn(doctype, runner.STAMPED_DOCTYPES)

	def test_department_brings_its_approvers_with_it(self):
		"""The cost this test used to NAME is the cost it now prevents.

		While Department stayed out, `leave_approvers`, `expense_approvers` and
		`shift_request_approver` did not follow the employees across, so
		department-based approver routing resolved to nobody. They are Table fields
		HRMS adds to Department as custom fields — absent from ERPNext's department
		JSON, and therefore absent from any check that reads only the JSON.

		They are the reason to mirror Department at all. A hierarchy with no
		approvers in it routes nothing, so `CHILD_TABLE_DOCTYPES` membership is not
		an optimisation here — without it this whole change would look done and
		deliver none of it.
		"""
		self.assertIn("Department", runner.CHILD_TABLE_DOCTYPES)


class TestHolidayAssignmentsAreDerivedNotMirrored(_RunnerTestCase):
	"""A Holiday List Assignment is derived data, so mirroring it was the wrong
	shape — and the wrong shape is what produced three workarounds.

	It is computed from `Employee.holiday_list` and `Company.default_holiday_list`,
	both of which the mirror already carries. HRMS derives it exactly that way in
	`v16_0.create_holiday_list_assignments`. Pulling it over the wire as well meant
	two routes to one state, and because the source predates the doctype the
	mirrored route could never work — which is what the 403, the 404 and the
	declared-absent list were each patching around.

	Deriving it locally also happens to be what the hub wants: holiday policy is
	HR's to own here, and derived rows carry no provenance stamp, so nothing
	reverts an HR decision on the next run.
	"""

	SEED_EXCLUDE = ("Employee",)

	def test_it_is_not_pulled_from_the_source(self):
		self.assertNotIn("Holiday List Assignment", runner.DEFAULT_SYNC_DOCTYPES)
		self.assertNotIn("Holiday List Assignment", runner.STAMPED_DOCTYPES)

	def test_nothing_declares_it_as_a_dependency_any_more(self):
		"""Leftover graph entries for a doctype nobody pulls would skip real work."""
		self.assertNotIn("Holiday List Assignment", runner.ROW_DEPENDENCIES)
		self.assertNotIn("Holiday List Assignment", runner.SYNC_DEPENDENCIES)

	def test_a_run_derives_them_afterwards(self):
		self.seed_parent("Company", "Acme", company_name="Acme")
		derived = []
		runner._derive_holiday_assignments = lambda: derived.append(True)
		self.addCleanup(setattr, runner, "_derive_holiday_assignments", runner._derive_holiday_assignments)

		runner.sync_instance(self.client({"Employee": EMPLOYEES}), doctypes=["Employee"], incremental=False)

		self.assertEqual(derived, [True])

	def test_a_derivation_failure_never_fails_the_run(self):
		"""Derived from data that has already landed — worth retrying next run, not
		worth discarding a successful pull over."""
		self.seed_parent("Company", "Acme", company_name="Acme")
		saved = runner._derive_holiday_assignments
		self.addCleanup(setattr, runner, "_derive_holiday_assignments", saved)
		runner._derive_holiday_assignments = lambda: (_ for _ in ()).throw(RuntimeError("nope"))

		result = runner.sync_instance(
			self.client({"Employee": EMPLOYEES}), doctypes=["Employee"], incremental=False
		)

		self.assertEqual(result["status"], "Completed")


class TestTheMirrorAdaptsToThisSitesSchema(_RunnerTestCase):
	"""Two shapes of schema drift, one root: the source's Employee is not this
	site's Employee, and the mirror was copying it verbatim.

	    Employee: HR-EMP-00282: (1054, "Unknown column 'custom_reports_to_name' in 'SET'")
	    Employee: HR-EMP-00115:  Performance Band cannot be "B2".

	`custom_reports_to_name` is a customisation on nasty-sg-dev that this hub has
	never had. An INSERT survives it — Frappe drops unknown keys in
	`get_valid_dict` — but an UPDATE goes through `db.set_value`, which builds a
	SET clause from whatever it is handed, so 100+ existing employees failed on
	every run. And a Select the source has widened rejects the whole document on
	insert, which is how E3 cost 173 people — and how B2, later confirmed a real
	band that was merely unoccupied, was briefly refused with it.

	Chasing these one value and one field at a time is endless. The mirror narrows
	each payload to what THIS site can actually store, and reports what it dropped
	— an employee arriving without one unrepresentable field beats an employee not
	arriving at all, and the report is what makes the difference visible rather
	than silent.
	"""

	SEED_EXCLUDE = ("Employee",)

	def test_a_column_this_site_does_not_have_is_dropped(self):
		payload, dropped = runner._narrow_to_local_schema(
			"Employee", {"employee_name": "Aisha", "custom_reports_to_name": "Someone"}
		)

		self.assertNotIn("custom_reports_to_name", payload)
		self.assertEqual(payload["employee_name"], "Aisha")
		self.assertIn("custom_reports_to_name", dropped)

	def test_a_select_value_this_site_cannot_represent_is_dropped(self):
		payload, dropped = runner._narrow_to_local_schema(
			"Employee", {"employee_name": "Aisha", "performance_band": "E3"}
		)

		self.assertNotIn("performance_band", payload)
		self.assertIn("performance_band", dropped)

	def test_a_select_value_this_site_does_know_is_kept(self):
		payload, _ = runner._narrow_to_local_schema("Employee", {"performance_band": "E2"})
		self.assertEqual(payload["performance_band"], "E2")

	def test_an_empty_select_value_is_always_allowed(self):
		payload, dropped = runner._narrow_to_local_schema("Employee", {"performance_band": ""})
		self.assertEqual(payload["performance_band"], "")
		self.assertEqual(dropped, {})

	def test_the_row_still_lands(self):
		"""The whole point: one unrepresentable field must not cost the record."""
		self.seed_parent("Company", "Acme", company_name="Acme")
		remote = [
			dict(EMPLOYEES[0], performance_band="E3", custom_reports_to_name="Someone"),
		]

		result = runner.sync_doctype(self.client({"Employee": remote}), "Employee")

		self.assertEqual(result["errored"], 0)
		self.assertEqual(result["inserted"], 1)
		self.assertNotIn("custom_reports_to_name", self.store.rows("Employee")["HR-EMP-0001"])

	def test_what_was_dropped_is_reported(self):
		"""Silently discarding a field is the hole; naming it is the fix."""
		self.seed_parent("Company", "Acme", company_name="Acme")
		remote = [dict(EMPLOYEES[0], custom_reports_to_name="Someone")]

		result = runner.sync_doctype(self.client({"Employee": remote}), "Employee")

		self.assertIn("custom_reports_to_name", result["dropped_fields"])

	def test_no_select_field_can_cost_a_whole_record(self):
		"""The general rule, stated once.

		The mirrored doctypes carry 23 Select fields between them. Before this,
		every one could reject an entire row on a value the source had and this site
		had not — `performance_band` is simply the one that fired. Widening the
		destination each time it happens is a queue, not a fix, and it points the
		correction in the wrong direction: E3 turned out to be an HR data-entry
		error on the source, so the hub had been widened to accept bad data.
		"""
		for value in ("E3", "anything-the-source-invents"):
			with self.subTest(value=value):
				payload, dropped = runner._narrow_to_local_schema(
					"Employee", {"employee_name": "Aisha", "performance_band": value}
				)
				self.assertEqual(payload["employee_name"], "Aisha", "the record must still land")
				self.assertNotIn("performance_band", payload)
				self.assertIn("performance_band", dropped)

	def test_a_rejected_select_value_is_named_so_hr_can_correct_it(self):
		"""Naming the FIELD tells an operator something is wrong. Naming the VALUE
		tells HR what to go and fix.

		E3 was a data-entry mistake on the source, and the only way it surfaced was
		173 employees failing to load. Now the record lands and the run says which
		value it could not represent — the same information, without the loss, and
		pointed at the system that can actually correct it.
		"""
		self.seed_parent("Company", "Acme", company_name="Acme")
		remote = [
			dict(EMPLOYEES[0], performance_band="E3"),
			dict(EMPLOYEES[1], performance_band="B2"),
		]

		result = runner.sync_doctype(self.client({"Employee": remote}), "Employee")

		self.assertEqual(result["errored"], 0)
		report = result["dropped_fields"]
		# E3 is named for HR to fix at the source; B2 is a REAL band
		# (2026-08-18 ruling — unoccupied is not invalid) and lands intact.
		self.assertIn("performance_band (E3)", report)
		self.assertEqual(self.store.rows("Employee")["HR-EMP-0002"]["performance_band"], "B2")

	def test_a_missing_column_is_named_without_a_value(self):
		"""There is no offending value to report — the column simply is not here."""
		self.seed_parent("Company", "Acme", company_name="Acme")
		remote = [dict(EMPLOYEES[0], custom_reports_to_name="Someone")]

		result = runner.sync_doctype(self.client({"Employee": remote}), "Employee")

		self.assertIn("custom_reports_to_name", result["dropped_fields"])
		self.assertNotIn("custom_reports_to_name (", " ".join(result["dropped_fields"]))

	def test_the_provenance_stamp_is_never_narrowed_away(self):
		"""The one drop that must never be silent.

		Narrowing removes any column this site lacks — and on a site where
		`add_sync_provenance_fields` has not run, `synced_from_instance` IS such a
		column. Dropped quietly, every row lands unstamped: parity counts zero
		however many arrive, the write-block stops recognising mirrored rows and
		lets anyone edit them, and `_count_local_orphans` sees nothing. A silent
		success that has broken three separate guarantees at once.

		Loud is the only safe behaviour: the row fails, the run reports it, and
		`bench migrate` is the fix.
		"""
		with self.assertRaises(Exception) as ctx:
			runner._narrow_to_local_schema(
				"Employee",
				{"employee_name": "Aisha", runner.PROVENANCE_FIELD: "nasty-live"},
				stamped=True,
				columns={"employee_name"},
			)

		self.assertIn(runner.PROVENANCE_FIELD, str(ctx.exception))

	def test_an_unstamped_doctype_is_unaffected(self):
		"""Masters carry no stamp by design, so their payloads never contain one."""
		payload, _dropped = runner._narrow_to_local_schema("Holiday List", {"holiday_list_name": "2026 MY"})
		self.assertEqual(payload, {"holiday_list_name": "2026 MY"})

	def test_a_child_table_is_never_mistaken_for_a_missing_column(self):
		"""The regression this shipped with.

		`meta.get_valid_columns()` lists PARENT columns, and a child table is not
		one — its rows live in their own table. So narrowing stripped `holidays`,
		`breaks`, `overtime_rates` and `repeat_on_days`, and the run said so plainly:

		    Holiday List: this site cannot store holidays — written without them

		A Holiday List without its holidays is the silent-wrong-answer this whole
		child-table path exists to prevent — every weekend counted as a working day,
		and nothing raising.
		"""
		payload, dropped = runner._narrow_to_local_schema(
			"Holiday List", {"holiday_list_name": "2026 MY", "holidays": [{"holiday_date": "2026-01-01"}]}
		)

		self.assertIn("holidays", payload)
		self.assertEqual(payload["holidays"], [{"holiday_date": "2026-01-01"}])
		self.assertNotIn("holidays", dropped)

	def test_narrowing_is_skipped_when_the_schema_cannot_be_read(self):
		"""Fails open: if meta is unavailable the payload passes through unchanged
		rather than the mirror silently writing nothing."""
		saved = runner._local_schema
		self.addCleanup(setattr, runner, "_local_schema", saved)
		runner._local_schema = lambda doctype: (_ for _ in ()).throw(RuntimeError("no meta"))

		payload, dropped = runner._narrow_to_local_schema("Employee", {"anything": 1})

		self.assertEqual(payload, {"anything": 1})
		self.assertEqual(dropped, {})


class TestALongFilterIsSplitAcrossRequests(_RunnerTestCase):
	"""`Employee Checkin: remote rejected the read (status=400)`.

	Employee Checkin has no company field, so it is scoped by the employees the
	Employee pass just mirrored — and that list goes into the GET query string. At
	116 employees it worked and the doctype reached parity; at 289 the request line
	grew past what the remote's proxy accepts and every checkin stopped arriving.

	400 is not transient and not retryable, so it would simply have stayed broken
	as the mirror got healthier — the worst kind of failure, the one that arrives
	with success.
	"""

	SEED_EXCLUDE = ("Employee",)

	def test_a_short_filter_is_sent_as_one_request(self):
		chunks = list(runner._split_filters({"employee": ("in", ["a", "b"])}))
		self.assertEqual(chunks, [{"employee": ("in", ["a", "b"])}])

	def test_a_long_filter_is_split(self):
		names = [f"HR-EMP-{i:05d}" for i in range(250)]

		chunks = list(runner._split_filters({"employee": ("in", names)}))

		self.assertGreater(len(chunks), 1)
		self.assertLessEqual(max(len(c["employee"][1]) for c in chunks), runner.MAX_FILTER_VALUES)

	def test_splitting_loses_nobody(self):
		names = [f"HR-EMP-{i:05d}" for i in range(250)]

		rebuilt = [
			n for chunk in runner._split_filters({"employee": ("in", names)}) for n in chunk["employee"][1]
		]

		self.assertEqual(rebuilt, names)

	def test_other_filters_ride_along_on_every_chunk(self):
		names = [f"HR-EMP-{i:05d}" for i in range(150)]

		chunks = list(runner._split_filters({"employee": ("in", names), "modified": (">", "2026-01-01")}))

		self.assertTrue(all(c["modified"] == (">", "2026-01-01") for c in chunks))

	def test_every_chunk_is_actually_requested(self):
		self.seed_parent("Company", "Acme", company_name="Acme")
		for i in range(runner.MAX_FILTER_VALUES + 5):
			self.store.tables.setdefault("Employee", {})[f"HR-EMP-{i:05d}"] = {
				"name": f"HR-EMP-{i:05d}",
				"company": "Acme",
				runner.PROVENANCE_FIELD: "nasty-live",
			}
		client = self.client({"Employee Checkin": []})

		runner.sync_doctype(
			client,
			"Employee Checkin",
			filters=runner.scope_filter("Employee Checkin", ["Acme"], "nasty-live"),
		)

		checkin_calls = [c for c in client.calls if c["doctype"] == "Employee Checkin"]
		self.assertGreaterEqual(len(checkin_calls), 2, "a long employee list must be split")


class TestSyncRunsInTheBackground(unittest.TestCase):
	"""A full pull cannot run inside an HTTP request.

	verifica-live, 2026-08-17: the operator clicked "Sync Employee Data" and got
	"Request Timed Out". A full pull of ~10^2 employees plus their attendance,
	check-ins and ledger takes minutes; the gateway gives the request ~2. Worse
	than the wait, the worker is KILLED rather than allowed to raise, so
	`sync_instance`'s `finally` never runs and the `HRMS Sync Run` row stays
	`Running` forever — indistinguishable from a live run.

	The long queue's ceiling is 1500s against the gateway's ~120s, and the pull
	then owns its own lifetime instead of borrowing a request's.
	"""

	def setUp(self):
		import frappe

		self.enqueued = []
		#: What rq would say about this instance's job, and how many workers are
		#: consuming the queue. An Exception value means introspection blew up.
		self.job_status = None
		self.workers = 1

		def fake_enqueue(method, **kwargs):
			self.enqueued.append({"method": method, **kwargs})
			return types.SimpleNamespace(id=kwargs.get("job_id"))

		def probe(value):
			if isinstance(value, Exception):
				raise value
			return value

		self._saved = (
			getattr(frappe, "enqueue", None),
			getattr(frappe, "throw", None),
			getattr(frappe, "get_all", None),
			runner._job_status,
			runner._queue_workers,
		)
		frappe.enqueue = fake_enqueue
		frappe.throw = lambda msg, *a, **kw: (_ for _ in ()).throw(ValueError(msg))
		frappe.get_all = lambda *a, **kw: []
		runner._job_status = lambda job_id: probe(self.job_status)
		runner._queue_workers = lambda queue=None: probe(self.workers)
		# unfenced, same as _RunnerTestCase: this class's frappe stub has no
		# session for the fence to resolve, and fence behaviour is not what
		# these queue tests are about
		self._saved_fence = runner.require_unfenced
		runner.require_unfenced = lambda *a, **k: None
		self.addCleanup(setattr, runner, "require_unfenced", self._saved_fence)
		self.addCleanup(self._restore)

	def _restore(self):
		import frappe

		(
			frappe.enqueue,
			frappe.throw,
			frappe.get_all,
			runner._job_status,
			runner._queue_workers,
		) = self._saved

	def test_it_queues_rather_than_running_inline(self):
		result = runner.enqueue_sync("Nasty-Dev", incremental=0)

		self.assertTrue(result["queued"])
		self.assertEqual(len(self.enqueued), 1)
		self.assertEqual(self.enqueued[0]["method"], "hrms.sync.runner.run_sync")
		self.assertEqual(self.enqueued[0]["instance_name"], "Nasty-Dev")

	def test_it_uses_the_long_queue_with_a_real_ceiling(self):
		"""`default` is 300s — still short of a full pull. `long` is 1500s."""
		runner.enqueue_sync("Nasty-Dev")

		self.assertEqual(self.enqueued[0]["queue"], "long")
		self.assertGreaterEqual(self.enqueued[0]["timeout"], 1500)

	def test_the_job_is_named_per_instance(self):
		"""Two different sources may legitimately sync at once."""
		runner.enqueue_sync("Nasty-Dev")
		runner.enqueue_sync("Other-ERP")

		self.assertEqual(len(self.enqueued), 2)
		self.assertNotEqual(self.enqueued[0]["job_id"], self.enqueued[1]["job_id"])

	def test_a_blank_instance_is_refused_before_queueing(self):
		"""Otherwise the failure surfaces minutes later, in a worker log."""
		with self.assertRaises(ValueError):
			runner.enqueue_sync("")
		self.assertEqual(self.enqueued, [])

	def test_a_queued_job_nobody_will_ever_take_is_reported_not_hidden(self):
		"""verifica-live, 2026-08-17: the button said "A sync is already in
		progress" and the HRMS Sync Run list held nothing but a week-old Partial.

		The job was sitting QUEUED on a queue with no worker consuming it. With rq
		deduplication that was not merely slow, it was a LOCKOUT: every later click
		saw a live job id and refused, so the button was dead for good and the
		operator had no way to tell a busy sync from a dead one. The queue's own
		health has to be part of the answer.
		"""
		self.job_status = "queued"
		self.workers = 0

		result = runner.enqueue_sync("Nasty-Dev")

		self.assertFalse(result["queued"])
		self.assertEqual(result["reason"], "no_worker")

	def test_a_queued_job_with_a_live_worker_is_simply_waiting(self):
		self.job_status = "queued"
		self.workers = 2

		result = runner.enqueue_sync("Nasty-Dev")

		self.assertFalse(result["queued"])
		self.assertEqual(result["reason"], "already_queued")
		self.assertEqual(self.enqueued, [], "a waiting job must not be duplicated")

	def test_nothing_is_queued_onto_a_queue_with_no_worker(self):
		"""Reporting "queued" for work that cannot start is the lie that cost an
		afternoon. Refuse and name the reason instead."""
		self.workers = 0

		result = runner.enqueue_sync("Nasty-Dev")

		self.assertFalse(result["queued"])
		self.assertEqual(result["reason"], "no_worker")
		self.assertEqual(self.enqueued, [])

	def test_force_clears_a_stuck_job_and_queues_a_fresh_one(self):
		"""The escape hatch for a job that is queued and never starts.

		Without it the only cure is a bench console, which a Frappe Cloud operator
		does not have — so "it is stuck" would mean "raise a ticket and wait".
		"""
		self.job_status = "queued"
		self.workers = 1
		cleared = []
		runner._clear_job = lambda job_id: cleared.append(job_id)

		result = runner.enqueue_sync("Nasty-Dev", force=1)

		self.assertTrue(result["queued"])
		self.assertEqual(cleared, ["hrms-sync-Nasty-Dev"])
		self.assertEqual(len(self.enqueued), 1)

	def test_force_never_interrupts_a_run_that_is_genuinely_running(self):
		"""Force is for a stuck QUEUE, not for killing live work mid-write."""
		import frappe

		frappe.get_all = lambda *a, **kw: [{"name": "SYNC-00009", "started_at": NOW}]

		result = runner.enqueue_sync("Nasty-Dev", force=1)

		self.assertFalse(result["queued"])
		self.assertEqual(result["reason"], "already_running")
		self.assertEqual(self.enqueued, [])

	def test_an_unknown_queue_state_never_blocks_the_operator(self):
		"""Redis unreachable, rq changed, whatever: an introspection failure must
		fail OPEN. A sync that runs twice is idempotent; a button that can never be
		pressed is not recoverable from the UI at all."""
		self.job_status = RuntimeError("redis is unreachable")
		self.workers = RuntimeError("redis is unreachable")

		result = runner.enqueue_sync("Nasty-Dev")

		self.assertTrue(result["queued"])
		self.assertEqual(len(self.enqueued), 1)

	def test_the_enqueue_endpoint_is_post_only(self):
		import ast

		tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
		functions = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
		methods = []
		for decorator in functions["enqueue_sync"].decorator_list:
			if isinstance(decorator, ast.Call):
				for keyword in decorator.keywords:
					if keyword.arg == "methods":
						methods = [element.value for element in keyword.value.elts]

		self.assertEqual(methods, ["POST"], "enqueue_sync starts a pull; it must be POST-only")


class TestAFailedStartStillLeavesEvidence(_RunnerTestCase):
	"""verifica-live, 2026-08-17 13:02: "Sync queued". 13:03: still one run record,
	dated a week earlier.

	`run_sync` built the `RemoteInstanceClient` — which resolves the URL and
	decrypts the credentials, and raises on a bad secret, a disabled instance or an
	unreachable host — BEFORE anything wrote a run record. In a web request that
	surfaced as a red dialog. In a background job it surfaces as nothing at all:
	the job dies, the operator sees no record, and cannot tell "never started" from
	"still running".

	A run that cannot start is still a run, and has to say so.
	"""

	SEED_EXCLUDE = ("Employee",)

	def test_a_client_that_cannot_be_built_still_records_a_failed_run(self):
		def explode(instance_name):
			raise RuntimeError("remote rejected the read (status=401)")

		with self.assertRaises(RuntimeError):
			runner.run_sync_with_client("Nasty-Dev", explode)

		runs = list(self.store.rows("HRMS Sync Run").values())
		self.assertEqual(len(runs), 1)
		self.assertEqual(runs[0]["status"], "Failed")
		self.assertIn("401", runs[0]["error_log"])

	def test_the_recorded_failure_names_the_instance(self):
		def explode(instance_name):
			raise RuntimeError("boom")

		with self.assertRaises(RuntimeError):
			runner.run_sync_with_client("Nasty-Dev", explode)

		runs = list(self.store.rows("HRMS Sync Run").values())
		self.assertEqual(runs[0]["source_instance"], "Nasty-Dev")

	def test_a_working_client_records_nothing_extra(self):
		"""The guard must not double-count a run that started normally."""
		self.seed_parent("Company", "Acme", company_name="Acme")
		client = self.client({"Employee": EMPLOYEES})

		runner.run_sync_with_client("nasty-live", lambda name: client, doctypes=["Employee"])

		self.assertEqual(len(self.store.rows("HRMS Sync Run")), 1)


class TestTheOperatorIsToldWhenItFinishes(_RunnerTestCase):
	"""Answering "will I get notified?" — previously, no.

	A run takes minutes and the operator was expected to sit on a list view and
	guess. The bell is the one place a Desk user already looks, and it survives
	them closing the tab.
	"""

	SEED_EXCLUDE = ("Employee",)

	def test_finishing_a_run_notifies_whoever_asked_for_it(self):
		self.seed_parent("Company", "Acme", company_name="Acme")

		runner.sync_instance(self.client({"Employee": EMPLOYEES}), doctypes=["Employee"], incremental=False)

		logs = list(self.store.rows("Notification Log").values())
		self.assertEqual(len(logs), 1)
		self.assertIn("nasty-live", logs[0]["subject"])

	def test_a_notification_failure_never_breaks_the_run(self):
		"""Telling somebody is strictly less important than the pull itself."""
		self.seed_parent("Company", "Acme", company_name="Acme")
		saved = runner._notify_run_finished
		self.addCleanup(setattr, runner, "_notify_run_finished", saved)
		runner._notify_run_finished = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("no bell"))

		result = runner.sync_instance(
			self.client({"Employee": EMPLOYEES}), doctypes=["Employee"], incremental=False
		)

		self.assertEqual(result["status"], "Completed")


class TestStaleRunsAreClosedOut(_RunnerTestCase):
	"""A killed worker leaves `Running` behind forever.

	`_finish_run` is called from a `finally`, so a run only stays `Running` when
	the process was killed rather than allowed to raise — a gateway timeout, an rq
	job timeout, or a redeploy mid-run. That row then looks live for ever, and the
	operator cannot tell a stuck run from a working one.

	Safe to close out at the start of the next run because `enqueue_sync`
	deduplicates per instance: at most one run per source is ever genuinely in
	flight, and this only executes at the start of that one.
	"""

	SEED_EXCLUDE = ("Employee",)

	def test_an_orphaned_running_row_is_marked_failed(self):
		self.store.tables.setdefault("HRMS Sync Run", {})["SYNC-00009"] = {
			"name": "SYNC-00009",
			"source_instance": "nasty-live",
			"status": "Running",
		}

		runner._close_stale_runs("nasty-live")

		self.assertEqual(self.store.rows("HRMS Sync Run")["SYNC-00009"]["status"], "Failed")

	def test_a_finished_run_is_never_touched(self):
		for name, status in (("SYNC-1", "Completed"), ("SYNC-2", "Partial"), ("SYNC-3", "Failed")):
			self.store.tables.setdefault("HRMS Sync Run", {})[name] = {
				"name": name,
				"source_instance": "nasty-live",
				"status": status,
			}

		runner._close_stale_runs("nasty-live")

		rows = self.store.rows("HRMS Sync Run")
		self.assertEqual(rows["SYNC-1"]["status"], "Completed")
		self.assertEqual(rows["SYNC-2"]["status"], "Partial")

	def test_another_instances_run_is_never_touched(self):
		self.store.tables.setdefault("HRMS Sync Run", {})["SYNC-OTHER"] = {
			"name": "SYNC-OTHER",
			"source_instance": "some-other-erp",
			"status": "Running",
		}

		runner._close_stale_runs("nasty-live")

		self.assertEqual(self.store.rows("HRMS Sync Run")["SYNC-OTHER"]["status"], "Running")

	def test_starting_a_run_closes_the_stale_ones_first(self):
		self.store.tables.setdefault("HRMS Sync Run", {})["SYNC-STUCK"] = {
			"name": "SYNC-STUCK",
			"source_instance": "nasty-live",
			"status": "Running",
		}

		runner.sync_instance(self.client({"Employee": []}), doctypes=["Employee"], incremental=False)

		self.assertEqual(self.store.rows("HRMS Sync Run")["SYNC-STUCK"]["status"], "Failed")


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


class TestTheMirrorNeverWalksALifecycle(_RunnerTestCase):
	"""A mirrored row is an end state, so no submit hook may run to reach it.

	Frappe derives `_action` from the docstatus it is handed. `insert()` with
	docstatus 1 therefore means `_action == "submit"`, and `on_submit` runs on THIS
	site — re-doing work the source instance already did. Measured on a real site,
	not inferred: inserting one submitted Leave Allocation created a Leave Ledger
	Entry; inserting it as a draft and then setting the docstatus created none.

	That is a cascade, because every `on_submit` in this app writes into a doctype
	the mirror already holds at exact parity:

	    Leave Policy Assignment -> Leave Allocation -> Leave Ledger Entry
	    Leave Application       -> Attendance
	    Attendance Request      -> Attendance
	    Shift Request           -> Shift Assignment

	Locally generated rows would stack on top of mirrored ones and roughly double
	the leave balances, reported by a run that said `Completed`.

	It has not bitten yet only because the three submittables mirrored until now —
	Attendance, Leave Ledger Entry, Shift Assignment — define no `on_submit` at
	all. That is luck, and it runs out the moment the leave chain is mirrored, so
	the rule is pinned here rather than remembered later.
	"""

	SEED_EXCLUDE: ClassVar[tuple] = ("Leave Allocation",)

	def _insert(self, name, docstatus):
		"""Writes one row, returning the docstatus frappe saw at INSERT time.

		The distinction the whole rule rests on: what reaches `insert()` decides
		whether `on_submit` fires, and it cannot be read back off the row afterwards
		because the second write lands on the same dict.
		"""
		import frappe

		runner._write_row.dropped_fields = {}
		seen = {}
		original = self.store.get_doc

		def spy(data, name=None):
			if name is None:
				seen["docstatus"] = dict(data).get("docstatus")
			return original(data, name)

		frappe.get_doc = spy
		try:
			runner._write_row(
				"Leave Allocation",
				name,
				{"employee": "HR-EMP-0001", "leave_type": "Annual Leave", "docstatus": docstatus},
			)
		finally:
			frappe.get_doc = original
		return seen["docstatus"]

	def test_a_submitted_row_reaches_insert_as_a_draft(self):
		self.assertEqual(
			self._insert("HR-LA-9001", 1),
			0,
			"a submitted row must be inserted as a draft, or frappe runs on_submit",
		)

	def test_a_cancelled_row_reaches_insert_as_a_draft_too(self):
		"""This case used to insert at docstatus 1 and then cancel, because frappe
		refuses a direct insert at 2. Going through draft removes the exception
		rather than keeping a second mechanism beside the rule."""
		self.assertEqual(self._insert("HR-LA-9002", 2), 0)

	def test_the_final_docstatus_is_applied_hook_free(self):
		for name, docstatus in (("HR-LA-9003", 1), ("HR-LA-9004", 2)):
			self._insert(name, docstatus)
			self.assertIn(
				("Leave Allocation", name, {"docstatus": docstatus}),
				self.store.updates,
				f"docstatus {docstatus} must be applied by db.set_value, which runs no hooks",
			)

	def test_a_draft_row_is_written_once(self):
		"""No second write for the common case — drafts are already their end state."""
		self._insert("HR-LA-9005", 0)
		self.assertEqual([u for u in self.store.updates if u[1] == "HR-LA-9005"], [])


class TestCompaniesGetTheirHolidayCalendar(_RunnerTestCase):
	"""A mirrored company must end up pointing at a Holiday List.

	`MIRRORED_FIELDS["Company"]` is an identity projection because a local Company
	owns finance configuration a mirror must not overwrite. `default_holiday_list`
	was swept up in that, and it is not finance — it decides which calendar an
	employee's leave and attendance are measured against.

	The cost was exact and silent. `get_holiday_list_for_employee` reads
	`Employee.holiday_list` and falls back to `Company.default_holiday_list`; for
	any employee whose source relies on the company default both were empty here,
	so the PWA said "You have no upcoming holidays" in a month with two Malaysian
	public holidays in it. `_derive_holiday_assignments` reads the same two fields
	and so derived nothing either. Nothing raised.
	"""

	SEED_EXCLUDE: ClassVar[tuple] = ()

	class _Remote:
		def __init__(self, docs):
			self.docs = docs

		def get_doc(self, doctype, name):
			return self.docs.get((doctype, name), {})

	def _run(self, remote_docs, seed_companies, seed_lists=("2026 MY",)):
		for company, existing in seed_companies.items():
			self.store.tables.setdefault("Company", {})[company] = {
				"name": company,
				"default_holiday_list": existing,
			}
		for name in seed_lists:
			self.store.tables.setdefault("Holiday List", {})[name] = {"name": name}
		return runner._mirror_company_holiday_defaults(self._Remote(remote_docs))

	def test_an_unset_company_takes_the_sources_list(self):
		updated = self._run({("Company", "Acme"): {"default_holiday_list": "2026 MY"}}, {"Acme": None})
		self.assertEqual(updated, 1)
		self.assertEqual(self.store.tables["Company"]["Acme"]["default_holiday_list"], "2026 MY")

	def test_an_existing_choice_is_never_overwritten(self):
		"""HR picking a calendar on this hub is a decision, and the create-only rule
		that protects the rest of the Company record protects this too."""
		updated = self._run(
			{("Company", "Acme"): {"default_holiday_list": "2026 MY"}}, {"Acme": "HR's own list"}
		)
		self.assertEqual(updated, 0)
		self.assertEqual(self.store.tables["Company"]["Acme"]["default_holiday_list"], "HR's own list")

	def test_a_list_that_did_not_land_here_is_not_linked(self):
		"""A dangling default is no better than the empty field it replaced — and
		it is worse, because it looks configured."""
		updated = self._run({("Company", "Acme"): {"default_holiday_list": "2026 SG"}}, {"Acme": None})
		self.assertEqual(updated, 0)
		self.assertIsNone(self.store.tables["Company"]["Acme"]["default_holiday_list"])

	def test_a_remote_that_errors_does_not_stop_the_others(self):
		class Exploding(self._Remote):
			def get_doc(self, doctype, name):
				if name == "Boom":
					raise RuntimeError("remote refused")
				return super().get_doc(doctype, name)

		for company in ("Boom", "Acme"):
			self.store.tables.setdefault("Company", {})[company] = {"name": company}
		self.store.tables.setdefault("Holiday List", {})["2026 MY"] = {"name": "2026 MY"}
		updated = runner._mirror_company_holiday_defaults(
			Exploding({("Company", "Acme"): {"default_holiday_list": "2026 MY"}})
		)
		self.assertEqual(updated, 1)

	def test_it_runs_before_the_assignments_are_derived(self):
		"""The derivation reads this exact field, so the order is load-bearing."""
		source = (HRMS_ROOT / "sync" / "runner.py").read_text(encoding="utf-8")
		body = source[source.index("def sync_instance") :]
		self.assertLess(
			body.index("_mirror_company_holiday_defaults("),
			body.index("_derive_holiday_assignments()"),
			"holiday defaults must be mirrored before assignments are derived from them",
		)


class TestDepartmentKeepsItsShapeAndNotItsArithmetic(_RunnerTestCase):
	"""A NestedSet mirrors as parent links, never as positions.

	Department was kept out of the mirror entirely for this reason, and the reason
	was sound: `lft`/`rgt` are not data, they are a position in the SOURCE's tree.
	Copied here they describe a shape this site does not have, and every ancestor
	and descendant query — "everyone under this department", which is how approver
	routing and team scoping resolve — answers confidently from them. Nothing
	raises. That is why it was excluded where a dangling link would have been
	tolerated.

	It is no longer a reason to leave 289 employees pointing at a department this
	site does not have. The shape (`parent_department`) is mirrored, the arithmetic
	is dropped at the payload, and `_rebuild_department_tree` recomputes it once the
	whole pass has landed — which is the only correct moment, because rows arrive in
	`modified` order and a child routinely precedes its parent.
	"""

	def test_the_positions_are_never_copied(self):
		payload = runner._mirror_payload(
			{
				"name": "Engineering - NW",
				"department_name": "Engineering",
				"parent_department": "All Departments - NW",
				"company": "Nasty Worldwide Sdn Bhd",
				"lft": 41,
				"rgt": 58,
				"old_parent": "Operations - NW",
			},
			"nasty-live",
			"Department",
		)
		for positional in ("lft", "rgt", "old_parent"):
			self.assertNotIn(
				positional,
				payload,
				f"{positional} describes the source's tree, not this one",
			)

	def test_the_shape_is_copied(self):
		"""Dropping the parent link as well would mirror a flat list of departments
		and call it a hierarchy."""
		payload = runner._mirror_payload(
			{"name": "Engineering - NW", "parent_department": "All Departments - NW"},
			"nasty-live",
			"Department",
		)
		self.assertEqual(payload["parent_department"], "All Departments - NW")

	def test_a_department_precedes_the_employees_that_point_at_it(self):
		order = list(runner.DEFAULT_SYNC_DOCTYPES)
		self.assertLess(order.index("Department"), order.index("Employee"))

	def test_a_department_is_not_gated_on_its_parent_landing_first(self):
		"""`modified` order means a child routinely arrives before its parent.
		Gating on it would skip real departments for an ordering accident."""
		self.assertNotIn("parent_department", runner.ROW_DEPENDENCIES["Department"])
		self.assertEqual(runner.ROW_DEPENDENCIES["Department"]["company"], "Company")

	def test_the_rebuild_cannot_fail_the_run(self):
		"""The departments are already written and their links already right; a
		failed renumber is an alarm, not a reason to discard 8,000 pulled rows."""
		source = (HRMS_ROOT / "sync" / "runner.py").read_text(encoding="utf-8")
		call = source.index("_rebuild_department_tree()", source.index("def sync_instance"))
		self.assertIn("try:", source[call - 200 : call])
		self.assertIn("except Exception", source[call : call + 200])


class TestAnUnconstrainedSelectConstrainsNothing(unittest.TestCase):
	"""A Select declaring no options must not narrow anything.

	Frappe skips its own check for exactly this case — `_validate_selects` reads
	`if ... or not df.options: continue` — so the site stores any value in such a
	field. Reading it as a constraint produced the option set `{""}`: only the
	empty string storable, every real value dropped. That is the mirror being
	STRICTER than the site it writes to, and silent by design, because the value
	goes missing and the row still saves.

	It cost every Shift Location its timezone. `Shift Location.timezone` is a
	Select with no options, so Asia/Dubai, Asia/Kuala_Lumpur and CST6CDT were all
	discarded from a field this site stores perfectly well — on a hub whose job
	includes knowing which wall clock a punch was measured against.

	Drives the REAL `_local_schema` against a stub meta; the suite above replaces
	that function wholesale, so this is the only place it is exercised.
	"""

	class _Field:
		def __init__(self, fieldname, fieldtype, options=None):
			self.fieldname = fieldname
			self.fieldtype = fieldtype
			self.options = options

	class _Meta:
		def __init__(self, fields):
			self.fields = fields

		def get_valid_columns(self):
			return [f.fieldname for f in self.fields]

		def get_table_fields(self):
			return []

	def _schema(self, *fields):
		import frappe

		meta = self._Meta(list(fields))
		saved = getattr(frappe, "get_meta", None)
		frappe.get_meta = lambda doctype: meta
		try:
			return runner._local_schema("Shift Location")
		finally:
			frappe.get_meta = saved

	def test_a_select_without_options_is_left_alone(self):
		_columns, selects = self._schema(self._Field("timezone", "Select", None))
		self.assertNotIn(
			"timezone",
			selects,
			"a Select with no options constrains nothing — frappe does not check it either",
		)

	def test_an_options_string_of_only_blanks_is_left_alone_too(self):
		"""`"\\n"` is how an emptied Select round-trips through the fixture."""
		_columns, selects = self._schema(self._Field("timezone", "Select", "\n"))
		self.assertNotIn("timezone", selects)

	def test_a_real_option_list_still_narrows(self):
		"""The point is not to stop narrowing — performance_band must still drop
		E3, which is the whole reason the mechanism exists."""
		_columns, selects = self._schema(self._Field("performance_band", "Select", "\nB\nB2\nC"))
		self.assertEqual(selects["performance_band"], {"", "B", "B2", "C"})

	def test_the_column_is_kept_either_way(self):
		"""Narrowing is about VALUES. The field is storable regardless."""
		columns, _selects = self._schema(self._Field("timezone", "Select", None))
		self.assertIn("timezone", columns)


if __name__ == "__main__":
	unittest.main(verbosity=2)
