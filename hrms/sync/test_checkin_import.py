"""`hrms.sync.checkin_import` — source punches come in after cutover, add-only.

Staff still punch on the source ERP after this hub took over writing. Those
punches must reach the hub and count toward attendance, without ever touching a
punch the hub already holds:

* I1 a punch is (employee, time to the second, log_type), never its name; the
  import inserts under the hub's own autoname, records "<instance>::<source
  name>" in `source_checkin` — UNIQUE, so a racing importer's duplicate-key
  error is "already imported", never a second row — never updates or deletes,
  and a re-run is a no-op;
* I3 an imported punch is unstamped (attendance reads it), the hub resolves its
  shift, and phone-punch checks do not reject it;
* I4 the window is punch TIME, not `modified`; refused rows are reported;
* I5 any local Employee whose name is the source employee id is in scope;
* I6 no path touches a local punch, and no name is forced.

Bench-free: `frappe` is stubbed and every frappe call this module makes lands on
a small in-memory site below. Run it as a FILE:

    PYTHONPATH=. python3 hrms/sync/test_checkin_import.py
"""

import datetime
import json
import pathlib
import re
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _frappe_stub

_frappe_stub.install()

import frappe

from hrms.sync import checkin_import as ci

D = datetime.datetime
TODAY = datetime.date(2026, 9, 14)
INSTANCE = "nasty-live"


# --- an in-memory site ----------------------------------------------------------


def _moment(value, end=False) -> str:
	"""Comparable 'YYYY-MM-DD HH:MM:SS'. A bare date as the upper bound of a
	`between` reaches the end of that day, which is what Frappe does for a
	Datetime field."""
	if isinstance(value, D):
		return value.strftime("%Y-%m-%d %H:%M:%S")
	if isinstance(value, datetime.date):
		value = value.isoformat()
	text = str(value).replace("T", " ")
	if len(text) == 10:
		return text + (" 23:59:59" if end else " 00:00:00")
	return text[:19]


def _matches(row, filters) -> bool:
	for field, condition in (filters or {}).items():
		value = row.get(field)
		if isinstance(condition, list | tuple):
			operator, operand = condition[0], condition[1]
			if operator == "in":
				ok = value in operand
			elif operator == "between":
				ok = value is not None and _moment(operand[0]) <= _moment(value) <= _moment(
					operand[1], end=True
				)
			elif operator == "is":
				ok = bool(value) == (operand == "set")
			elif operator == "<":
				ok = value is not None and value < operand
			elif operator == ">=":
				ok = value is not None and _moment(value) >= _moment(operand)
			elif operator == "like":
				pattern = "".join(
					".*" if ch == "%" else "." if ch == "_" else re.escape(ch) for ch in operand
				)
				ok = value is not None and re.fullmatch(pattern, str(value), re.DOTALL) is not None
			elif operator == "!=":
				ok = value != operand
			else:
				raise AssertionError(f"operator {operator} not modelled")
		else:
			ok = value == condition
		if not ok:
			return False
	return True


class FakeDB:
	def __init__(self, site):
		self.site = site
		self.set_values = []
		self.deletes = []
		self.savepoints = []
		self.rollbacks = []

	def savepoint(self, name):
		self.savepoints.append(name)

	def rollback(self, save_point=None):
		self.rollbacks.append(save_point)

	def set_value(self, *args, **kwargs):
		self.set_values.append(args)

	def delete(self, *args, **kwargs):
		self.deletes.append(args)

	def commit(self):
		pass

	def exists(self, doctype, filters):
		rows = [row for row in self.site.tables.get(doctype, {}).values() if _matches(row, filters)]
		return rows[0]["name"] if rows else None

	def sql(self, query, values=None, **kwargs):
		if "`tabHRMS ERP Instance`" in query and "for update nowait" in query:
			self.site.lock_requests.append((query, values))
			if self.site.locked:
				raise FakeLockTimeout("Lock wait timeout exceeded; NOWAIT")
			return [(values[0],)]
		raise AssertionError(f"sql not modelled: {query}")


class FakeLockTimeout(Exception):
	"""frappe.QueryTimeoutError: what MariaDB's NOWAIT raises on a held row."""


class FakeIntegrityError(Exception):
	"""pymysql.IntegrityError as MariaDB raises it: (1062, "Duplicate entry ...")."""


class FakeUniqueValidationError(Exception):
	"""frappe.UniqueValidationError(doctype, name, <IntegrityError>)."""


class FakeDuplicateEntryError(Exception):
	"""frappe.DuplicateEntryError(doctype, name, <IntegrityError>) — the PRIMARY key."""


class FakeCheckin:
	"""A new Employee Checkin. Records how it was inserted."""

	def __init__(self, site):
		self.__dict__["_site"] = site
		self.flags = types.SimpleNamespace()
		self.name = None

	def update(self, values):
		self.__dict__.update(values)

	def _row(self):
		return {k: v for k, v in self.__dict__.items() if not k.startswith("_") and k != "flags"}

	def insert(self, **kwargs):
		"""The database's rules, as MariaDB and Frappe apply them on insert."""
		site = self._site
		if self.time in site.fail_at:
			raise RuntimeError("Deadlock found when trying to get lock")
		key = self.__dict__.get("source_checkin")
		taken = {row.get("source_checkin") for row in site.tables["Employee Checkin"].values()}
		if key and (key in taken or key in site.committed_elsewhere):
			raise FakeUniqueValidationError(
				"Employee Checkin",
				None,
				FakeIntegrityError(1062, f"Duplicate entry '{key}' for key 'source_checkin'"),
			)
		site.counter += 1
		name = f"HUB-CKIN-{site.counter:04d}"
		if self.time in site.name_clash_at:
			raise FakeDuplicateEntryError(
				"Employee Checkin",
				name,
				FakeIntegrityError(1062, f"Duplicate entry '{name}' for key 'PRIMARY'"),
			)
		site.insert_calls.append({"kwargs": kwargs, "flags": dict(vars(self.flags))})
		self.name = name
		site.tables["Employee Checkin"][self.name] = self._row()
		return self

	def fetch_shift(self):
		self._site.fetch_shift_calls.append(self.name)
		self.shift = "Day"

	def save(self, **kwargs):
		self._site.saves.append((self.name, dict(vars(self.flags))))
		self._site.tables["Employee Checkin"][self.name] = self._row()
		return self


class FakeShift:
	name = "Day"

	def __init__(self):
		self.calls = []
		self.previews = []

	def has_incorrect_shift_config(self):
		return False

	def shift_day_result(self, employee, attendance_date, logs):
		self.previews.append((employee, attendance_date, [row.name for row in logs]))
		return types.SimpleNamespace(
			existing=types.SimpleNamespace(name="ATT-1"),
			eligible_logs=logs,
			status="Present",
			working_hours=15.27,
			late_entry=False,
			early_exit=False,
			in_time=D(2026, 9, 3, 8, 48, 3),
			out_time=D(2026, 9, 4, 1, 4),
			overtime_type="Weekday OT",
		)

	def mark_attendance_for_shift_logs(self, employee, attendance_date, logs):
		self.calls.append((employee, attendance_date, [row.name for row in logs]))
		return types.SimpleNamespace(name="HR-ATT-NEW")


class FakeSite:
	def __init__(self, employees=(), checkins=(), attendance=(), runs=(), deleted=()):
		"""`employees`: a name is an employee mirrored from INSTANCE; pass a dict to
		describe any other (unstamped, another instance's, Left)."""
		rows = [
			employee if isinstance(employee, dict) else {"name": employee, "synced_from_instance": INSTANCE}
			for employee in employees
		]
		self.tables = {
			"Employee": {row["name"]: dict(row) for row in rows},
			"Employee Checkin": {row["name"]: dict(row) for row in checkins},
			"Attendance": {row["name"]: dict(row) for row in attendance},
			"HRMS Sync Run": {row["name"]: dict(row) for row in runs},
			"Deleted Document": {row["name"]: dict(row) for row in deleted},
		}
		self.db = FakeDB(self)
		self.locked = False
		self.lock_requests = []
		#: `source_checkin` keys another importer committed that this transaction's
		#: snapshot cannot see: invisible to every read, enforced by the index.
		self.committed_elsewhere = set()
		self.counter = 0
		self.fail_at = set()
		self.name_clash_at = set()
		self.insert_calls = []
		self.fetch_shift_calls = []
		self.saves = []
		self.only_for_calls = []
		self.get_all_calls = []
		self.shift = FakeShift()

	def get_all(self, doctype, filters=None, fields=None, pluck=None, order_by=None, limit=None, **kwargs):
		self.get_all_calls.append((doctype, filters))
		rows = [row for row in self.tables.get(doctype, {}).values() if _matches(row, filters)]
		if order_by:
			field = order_by.split()[0]
			rows.sort(
				key=lambda row: _moment(row.get(field) or ""),
				reverse=doctype == "HRMS Sync Run" and "desc" in order_by,
			)
		if limit:
			rows = rows[:limit]
		if pluck:
			return [row.get(pluck) for row in rows]
		if fields:
			return [frappe._dict({f: row.get(f) for f in fields}) for row in rows]
		return [frappe._dict(row) for row in rows]

	def new_doc(self, doctype):
		assert doctype == "Employee Checkin", doctype
		return FakeCheckin(self)

	def get_doc(self, doctype, name=None):
		assert doctype == "Shift Type", doctype
		return self.shift

	def only_for(self, roles, *args, **kwargs):
		self.only_for_calls.append(roles)

	def patch(self):
		return mock.patch.multiple(
			frappe,
			db=self.db,
			get_all=self.get_all,
			new_doc=self.new_doc,
			get_doc=self.get_doc,
			only_for=self.only_for,
			session=types.SimpleNamespace(user="hr.manager@example.com"),
			flags=types.SimpleNamespace(),
			QueryTimeoutError=FakeLockTimeout,
		)

	def checkins(self):
		return self.tables["Employee Checkin"]


class FakeClient:
	instance_name = INSTANCE

	def __init__(self, punches):
		self.punches = punches
		self.calls = []

	def get_list(self, doctype, filters=None, fields=None, limit=None, start=0, order_by=None):
		self.calls.append({"doctype": doctype, "filters": filters})
		if doctype != "Employee Checkin":
			return []
		return [dict(row) for row in self.punches if _matches(row, filters)]


def punch(employee, time, log_type, name, **extra):
	return {"employee": employee, "time": time, "log_type": log_type, "name": name, **extra}


class _SiteCase(unittest.TestCase):
	def use(self, site):
		self.site = site
		patcher = site.patch()
		patcher.start()
		self.addCleanup(patcher.stop)
		scope = mock.patch.object(ci, "_remote_scope", lambda client, instance, employee: None)
		scope.start()
		self.addCleanup(scope.stop)
		return site

	def run_import(self, client):
		return ci.import_source_checkins(client, INSTANCE, today=TODAY)


# --- I1 / I5: the plan, pure ------------------------------------------------------


class TestPlanImport(unittest.TestCase):
	def test_a_source_punch_missing_here_is_planned_for_insert(self):
		plan = ci.plan_import([punch("EMP-1", "2026-09-03 08:48:00", "IN", "R-1")], [], {"EMP-1"})
		self.assertEqual([entry["remote_name"] for entry in plan["insert"]], ["R-1"])

	def test_a_punch_already_here_by_its_natural_key_is_not_planned_again(self):
		plan = ci.plan_import(
			[punch("EMP-1", "2026-09-03 08:48:00.412", "IN", "R-1")],
			[punch("EMP-1", D(2026, 9, 3, 8, 48), "IN", "HUB-7")],
			{"EMP-1"},
		)
		self.assertEqual(plan["insert"], [])
		self.assertEqual(plan["matched"], 1)

	def test_a_hub_punch_under_the_same_name_is_not_the_same_punch(self):
		"""4 Sep 2026: both sites issue EMP-CKIN-09-2026-000012 from their own
		counters. A name match is no identity — the source punch still comes in."""
		plan = ci.plan_import(
			[punch("EMP-301", "2026-09-04 08:41:05", "IN", "EMP-CKIN-09-2026-000012")],
			[punch("EMP-12", D(2026, 9, 4, 9, 2, 11), "IN", "EMP-CKIN-09-2026-000012")],
			{"EMP-12", "EMP-301"},
		)
		self.assertEqual(len(plan["insert"]), 1)
		self.assertEqual(plan["refused"], [])

	def test_same_second_other_log_type_is_refused_not_inserted(self):
		plan = ci.plan_import(
			[punch("EMP-1", "2026-09-09 23:23:00", "OUT", "R-7")],
			[punch("EMP-1", D(2026, 9, 9, 23, 23), "IN", "HUB-3")],
			{"EMP-1"},
		)
		self.assertEqual(plan["insert"], [])
		self.assertEqual(
			[(row["remote_name"], row["reason"]) for row in plan["refused"]], [("R-7", "type_mismatch")]
		)

	def test_a_left_employees_punch_after_the_relieving_date_is_refused(self):
		employees = {"EMP-1": {"status": "Left", "relieving_date": "2026-09-03"}}
		plan = ci.plan_import(
			[
				punch("EMP-1", "2026-09-04 01:04:00", "OUT", "R-CLOSES-LAST-DAY"),
				punch("EMP-1", "2026-09-04 08:30:00", "IN", "R-AFTER"),
			],
			[],
			employees,
		)
		self.assertEqual([row["remote_name"] for row in plan["insert"]], ["R-CLOSES-LAST-DAY"])
		self.assertEqual(
			[(row["remote_name"], row["reason"]) for row in plan["refused"]], [("R-AFTER", "left")]
		)

	def test_a_source_employee_with_no_local_employee_is_reported_not_planned(self):
		plan = ci.plan_import(
			[
				punch("EMP-9", "2026-09-03 08:00:00", "IN", "R-1"),
				punch("EMP-9", "2026-09-03 17:00:00", "OUT", "R-2"),
			],
			[],
			{"EMP-1"},
		)
		self.assertEqual(plan["insert"], [])
		self.assertEqual(plan["unmapped"], {"EMP-9": 2})

	def test_a_punch_already_imported_under_its_source_name_is_not_planned_again(self):
		"""HR corrected the imported punch's time on the hub, so its natural key no
		longer matches; its `source_checkin` still does. Never re-inserted."""
		plan = ci.plan_import([punch("EMP-1", "2026-09-03 08:48:00", "IN", "R-1")], [], {"EMP-1"})
		plan = ci.drop_already_imported(plan, {"nasty-live::R-1": "HUB-7"}, INSTANCE)
		self.assertEqual(plan["insert"], [])
		self.assertEqual([row["local_name"] for row in plan["already_imported"]], ["HUB-7"])

	def test_the_same_source_name_from_another_instance_is_a_different_punch(self):
		plan = ci.plan_import([punch("EMP-1", "2026-09-03 08:48:00", "IN", "R-1")], [], {"EMP-1"})
		plan = ci.drop_already_imported(plan, {"nasty-dev::R-1": "HUB-7"}, INSTANCE)
		self.assertEqual(len(plan["insert"]), 1)

	def test_the_source_key_is_instance_qualified(self):
		self.assertEqual(
			ci.source_key("nasty-live", "EMP-CKIN-09-2026-000044"), "nasty-live::EMP-CKIN-09-2026-000044"
		)

	def test_only_a_duplicate_on_the_source_index_counts_as_already_imported(self):
		ours = FakeUniqueValidationError(
			"Employee Checkin",
			None,
			FakeIntegrityError(1062, "Duplicate entry 'nasty-live::R-1' for key 'source_checkin'"),
		)
		primary = FakeDuplicateEntryError(
			"Employee Checkin", "HUB-1", FakeIntegrityError(1062, "Duplicate entry 'HUB-1' for key 'PRIMARY'")
		)
		raw = FakeIntegrityError(1062, "Duplicate entry 'nasty-live::R-1' for key 'source_checkin'")
		self.assertTrue(ci.is_source_key_duplicate(ours))
		self.assertTrue(ci.is_source_key_duplicate(raw))
		self.assertFalse(ci.is_source_key_duplicate(primary), "a name clash would drop a punch without trace")
		self.assertFalse(ci.is_source_key_duplicate(RuntimeError("Deadlock found")))

	def test_a_past_midnight_out_belongs_to_the_previous_attendance_day(self):
		entry = {"time": D(2026, 9, 4, 1, 4), "log_type": "OUT"}
		self.assertEqual(ci.attendance_day(entry), datetime.date(2026, 9, 3))
		self.assertEqual(
			ci.attendance_day({"time": D(2026, 9, 4, 1, 4), "log_type": "IN"}), datetime.date(2026, 9, 4)
		)


# --- I1 / I3 / I4 / I5 / I6: the append-only write --------------------------------


class TestAppendOnlyImport(_SiteCase):
	def test_it_inserts_under_the_hubs_own_name_and_records_the_source_name(self):
		self.use(FakeSite(employees=["EMP-1"]))
		result = self.run_import(
			FakeClient([punch("EMP-1", "2026-09-10 18:02:00", "OUT", "EMP-CKIN-09-2026-000044")])
		)

		self.assertEqual(result["inserted"], 1)
		((name, row),) = self.site.checkins().items()
		self.assertNotEqual(name, "EMP-CKIN-09-2026-000044", "the source name must never be forced")
		self.assertEqual(row["source_checkin"], "nasty-live::EMP-CKIN-09-2026-000044")
		self.assertEqual(row["log_type"], "OUT", "the source's log type is kept as recorded")
		self.assertEqual(row["time"], D(2026, 9, 10, 18, 2))
		self.assertNotIn("set_name", self.site.insert_calls[0]["kwargs"])

	def test_it_never_updates_or_deletes_an_existing_punch(self):
		hub_row = punch("EMP-12", D(2026, 9, 4, 9, 2, 11), "IN", "EMP-CKIN-09-2026-000012", shift="Day")
		self.use(FakeSite(employees=["EMP-12", "EMP-301"], checkins=[hub_row]))

		self.run_import(
			FakeClient([punch("EMP-301", "2026-09-04 08:41:05", "IN", "EMP-CKIN-09-2026-000012")])
		)

		self.assertEqual(self.site.checkins()["EMP-CKIN-09-2026-000012"], hub_row)
		self.assertEqual(self.site.db.set_values, [])
		self.assertEqual(self.site.db.deletes, [])
		self.assertEqual(len(self.site.checkins()), 2)
		self.assertNotIn("EMP-CKIN-09-2026-000012", {name for name, _ in self.site.saves})

	def test_a_rerun_is_a_no_op(self):
		self.use(FakeSite(employees=["EMP-1"]))
		client = FakeClient(
			[
				punch("EMP-1", "2026-09-10 08:30:00", "IN", "R-1"),
				punch("EMP-1", "2026-09-10 18:00:00", "OUT", "R-2"),
			]
		)
		first = self.run_import(client)
		second = self.run_import(client)

		self.assertEqual(first["inserted"], 2)
		self.assertEqual(second["inserted"], 0)
		self.assertEqual(len(self.site.checkins()), 2)

	def test_imported_punches_are_not_stamped_so_attendance_reads_them(self):
		"""The hourly job, the sweeper and the write-block all key on the stamp:
		a stamped import would be locked AND ignored by attendance."""
		self.use(FakeSite(employees=["EMP-1"]))
		self.run_import(FakeClient([punch("EMP-1", "2026-09-10 08:30:00", "IN", "R-1")]))
		(row,) = self.site.checkins().values()
		self.assertFalse(row.get("synced_from_instance"))

	def test_phone_punch_checks_are_bypassed_and_the_hub_resolves_the_shift(self):
		self.use(FakeSite(employees=["EMP-1"]))
		self.run_import(FakeClient([punch("EMP-1", "2026-09-10 08:30:00", "IN", "R-1")]))

		((name, row),) = self.site.checkins().items()
		self.assertTrue(
			self.site.insert_calls[0]["flags"].get("ignore_validate"),
			"geofence and the phone rules would refuse a punch with no coordinates",
		)
		self.assertEqual(self.site.fetch_shift_calls, [name])
		self.assertEqual(row["shift"], "Day", "the resolved shift must be saved")

	def test_the_window_is_by_punch_time_not_modified(self):
		self.use(FakeSite(employees=["EMP-1"]))
		client = FakeClient(
			[
				punch("EMP-1", "2026-08-20 08:30:00", "IN", "R-OLD"),
				punch("EMP-1", "2026-09-01 08:30:00", "IN", "R-FIRST-DAY"),
			]
		)
		self.run_import(client)

		(call,) = [c for c in client.calls if c["doctype"] == "Employee Checkin"]
		self.assertNotIn("modified", call["filters"])
		self.assertEqual(call["filters"]["time"], ["between", ["2026-09-01", "2026-09-14"]])
		self.assertEqual(
			{row["source_checkin"] for row in self.site.checkins().values()}, {"nasty-live::R-FIRST-DAY"}
		)

	def test_an_employee_mirrored_from_this_instance_is_in_scope(self):
		self.use(FakeSite(employees=["HR-EMP-00318"]))
		result = self.run_import(FakeClient([punch("HR-EMP-00318", "2026-09-10 08:30:00", "IN", "R-1")]))
		self.assertEqual(result["inserted"], 1)

	def test_a_hub_native_employee_with_the_same_name_is_unmapped_never_written(self):
		"""The hub numbers its own employees from the same HR-EMP-* series: an
		unstamped HR-EMP-00401 here is not the source's HR-EMP-00401."""
		self.use(FakeSite(employees=[{"name": "HR-EMP-00401"}]))
		result = self.run_import(FakeClient([punch("HR-EMP-00401", "2026-09-10 08:30:00", "IN", "R-1")]))
		self.assertEqual(result["inserted"], 0)
		self.assertEqual(self.site.checkins(), {})
		self.assertEqual(result["outcomes"]["unmapped"], 1)

	def test_an_employee_mirrored_from_another_instance_is_unmapped_never_written(self):
		self.use(FakeSite(employees=[{"name": "HR-EMP-00401", "synced_from_instance": "nasty-dev"}]))
		result = self.run_import(FakeClient([punch("HR-EMP-00401", "2026-09-10 08:30:00", "IN", "R-1")]))
		self.assertEqual(result["inserted"], 0)
		self.assertEqual(result["outcomes"]["unmapped"], 1)

	def test_the_employee_fence_is_shared_with_the_report(self):
		self.use(
			FakeSite(
				employees=[
					"HR-EMP-00001",
					{"name": "HR-EMP-00401"},
					{"name": "HR-EMP-00402", "synced_from_instance": "nasty-dev"},
				]
			)
		)
		self.assertEqual(list(ci.local_employees(INSTANCE)), ["HR-EMP-00001"])

	def test_an_unmapped_source_employee_is_reported_and_does_not_count_against_the_run(self):
		self.use(FakeSite(employees=["EMP-1"]))
		result = self.run_import(FakeClient([punch("EMP-9", "2026-09-10 08:30:00", "IN", "R-1")]))
		self.assertEqual((result["orphaned"], result["missing_parents"]), (0, []))
		self.assertEqual(result["outcomes"]["unmapped"], 1)
		self.assertIn("unmapped EMP-9: 1 punch(es)", result["outcomes"]["sample"])
		self.assertEqual(result["inserted"], 0)

	def test_a_same_second_type_mismatch_is_refused_and_reported_not_contested(self):
		self.use(
			FakeSite(employees=["EMP-1"], checkins=[punch("EMP-1", D(2026, 9, 9, 23, 23), "IN", "HUB-3")])
		)
		result = self.run_import(FakeClient([punch("EMP-1", "2026-09-09 23:23:00", "OUT", "R-7")]))
		self.assertEqual(result["contested"], 0, "the watermark must not freeze over a punch")
		self.assertEqual(result["outcomes"]["refused"], 1)
		self.assertIn("R-7 (type_mismatch)", result["outcomes"]["sample"][0])
		self.assertEqual(result["inserted"], 0)

	def test_a_left_employees_punch_after_relieving_is_refused(self):
		self.use(
			FakeSite(
				employees=[
					{
						"name": "EMP-1",
						"synced_from_instance": INSTANCE,
						"status": "Left",
						"relieving_date": "2026-09-05",
					}
				]
			)
		)
		result = self.run_import(
			FakeClient(
				[
					punch("EMP-1", "2026-09-05 17:00:00", "OUT", "R-LAST-DAY"),
					punch("EMP-1", "2026-09-10 08:30:00", "IN", "R-AFTER"),
				]
			)
		)
		self.assertEqual(
			{row["source_checkin"] for row in self.site.checkins().values()}, {"nasty-live::R-LAST-DAY"}
		)
		self.assertEqual(result["outcomes"]["refused"], 1)
		self.assertIn("R-AFTER (left)", result["outcomes"]["sample"][0])

	def test_one_failing_insert_rolls_back_itself_and_the_rest_land(self):
		site = self.use(FakeSite(employees=["EMP-1"]))
		site.fail_at = {D(2026, 9, 10, 8, 30)}
		result = self.run_import(
			FakeClient(
				[
					punch("EMP-1", "2026-09-10 08:30:00", "IN", "R-1"),
					punch("EMP-1", "2026-09-10 18:00:00", "OUT", "R-2"),
				]
			)
		)
		self.assertEqual((result["inserted"], result["errored"]), (1, 0))
		self.assertEqual(result["outcomes"]["insert_errors"], 1)
		self.assertEqual(site.db.rollbacks, [ci.ROW_SAVEPOINT])
		self.assertIn("R-1", result["outcomes"]["sample"][0])

	# --- concurrency ------------------------------------------------------------

	def test_a_punch_another_importer_committed_unseen_is_already_imported_not_doubled(self):
		"""The plan and the re-check read a snapshot that cannot see the other
		importer's commit (cold meta cache, REPEATABLE READ). The unique index can:
		the insert's duplicate-key error is counted, never an error, never a row."""
		site = self.use(FakeSite(employees=["EMP-1"]))
		site.committed_elsewhere = {"nasty-live::R-1"}
		result = self.run_import(
			FakeClient(
				[
					punch("EMP-1", "2026-09-10 08:30:00", "IN", "R-1"),
					punch("EMP-1", "2026-09-10 18:00:00", "OUT", "R-2"),
				]
			)
		)
		self.assertEqual({row["source_checkin"] for row in site.checkins().values()}, {"nasty-live::R-2"})
		self.assertEqual((result["inserted"], result["skipped"]), (1, 1))
		self.assertEqual(result["outcomes"]["insert_errors"], 0)
		self.assertEqual(site.db.rollbacks, [ci.ROW_SAVEPOINT], "the batch goes on past the duplicate")

	def test_every_insert_has_its_own_savepoint(self):
		site = self.use(FakeSite(employees=["EMP-1"]))
		self.run_import(
			FakeClient(
				[
					punch("EMP-1", "2026-09-10 08:30:00", "IN", "R-1"),
					punch("EMP-1", "2026-09-10 18:00:00", "OUT", "R-2"),
				]
			)
		)
		self.assertEqual(site.db.savepoints, [ci.ROW_SAVEPOINT, ci.ROW_SAVEPOINT])

	def test_a_name_clash_is_an_error_not_already_imported(self):
		site = self.use(FakeSite(employees=["EMP-1"]))
		site.name_clash_at = {D(2026, 9, 10, 8, 30)}
		result = self.run_import(FakeClient([punch("EMP-1", "2026-09-10 08:30:00", "IN", "R-1")]))
		self.assertEqual(result["outcomes"]["insert_errors"], 1)
		self.assertEqual(result["skipped"], 0)

	def test_the_courtesy_lock_is_raw_sql_so_no_metadata_read_runs_first(self):
		site = self.use(FakeSite(employees=["EMP-1"]))
		self.run_import(FakeClient([punch("EMP-1", "2026-09-10 08:30:00", "IN", "R-1")]))
		((query, values),) = site.lock_requests
		self.assertIn("for update nowait", query)
		self.assertEqual(values, (INSTANCE,))

	def test_while_another_import_holds_the_lock_the_pass_writes_nothing_and_says_so(self):
		site = self.use(FakeSite(employees=["EMP-1"]))
		site.locked = True
		result = self.run_import(FakeClient([punch("EMP-1", "2026-09-10 08:30:00", "IN", "R-1")]))
		self.assertEqual(site.checkins(), {})
		self.assertTrue(result["outcomes"]["busy"])
		self.assertEqual(result["inserted"], 0)

	def test_a_punch_that_landed_after_the_plan_is_not_inserted_twice(self):
		"""`ignore_validate` skips the controller's duplicate check, so the insert
		re-checks the natural key itself."""
		site = self.use(
			FakeSite(employees=["EMP-1"], checkins=[punch("EMP-1", D(2026, 9, 10, 8, 30), "IN", "HUB-9")])
		)
		entry = {
			"employee": "EMP-1",
			"time": D(2026, 9, 10, 8, 30),
			"log_type": "IN",
			"remote_name": "R-1",
			"device_id": None,
		}
		self.assertIsNone(ci.insert_source_punch(entry, INSTANCE))
		self.assertEqual(list(site.checkins()), ["HUB-9"])
		self.assertEqual(ci._insert_all([entry], INSTANCE)["skipped"], 1)

	def test_the_result_carries_every_key_the_run_totals_read(self):
		self.use(FakeSite(employees=["EMP-1"]))
		result = self.run_import(FakeClient([]))
		for key in (
			"doctype",
			"pulled",
			"written",
			"skipped",
			"errored",
			"orphaned",
			"contested",
			"missing_parents",
			"row_errors",
			"schema_gaps",
			"dropped_fields",
		):
			self.assertIn(key, result)

	def test_the_source_field_is_the_one_the_install_path_creates(self):
		runner = (pathlib.Path(__file__).resolve().parent / "runner.py").read_text()
		self.assertIn(f'SOURCE_CHECKIN_FIELD = "{ci.SOURCE_FIELD}"', runner)


def completed_run(name, started_at, status="Completed"):
	return {"name": name, "source_instance": INSTANCE, "status": status, "started_at": started_at}


def deleted_punch(name, source_checkin, restored=0, creation="2026-09-10 12:00:00"):
	"""A Deleted Document as Frappe writes it: `data` is `frappe.as_json(doc.as_dict())`."""
	data = {
		"doctype": "Employee Checkin",
		"name": name,
		"employee": "EMP-1",
		"time": "2026-09-03 08:48:00",
		"log_type": "IN",
		"source_checkin": source_checkin,
	}
	return {
		"name": f"DEL-{name}",
		"deleted_doctype": "Employee Checkin",
		"deleted_name": name,
		"restored": restored,
		"creation": creation,
		"data": json.dumps(data, indent=1, sort_keys=True, separators=(",", ": ")),
	}


class TestSyncWindowCoversTheGap(_SiteCase):
	"""The pass reads back to the last Completed run, so skipped weekends lose no
	punch silently; past the 62-day cap the uncovered dates are named in the run."""

	def window_after(self, runs):
		self.use(FakeSite(employees=["EMP-1"], runs=runs))
		client = FakeClient([])
		result = self.run_import(client)
		(call,) = [c for c in client.calls if c["doctype"] == "Employee Checkin"]
		return call["filters"]["time"][1], result

	def test_a_run_5_days_ago_keeps_the_14_day_window_and_says_nothing(self):
		window, result = self.window_after([completed_run("SYNC-1", D(2026, 9, 9, 10, 0))])
		self.assertEqual(window, ["2026-09-01", "2026-09-14"])
		self.assertEqual(result["row_errors"], [])

	def test_a_run_30_days_ago_widens_the_window_to_a_day_before_it(self):
		window, result = self.window_after(
			[
				completed_run("SYNC-OLD", D(2026, 7, 1, 10, 0)),
				completed_run("SYNC-1", D(2026, 8, 15, 10, 0)),
				completed_run("SYNC-PARTIAL", D(2026, 9, 7, 10, 0), status="Partial"),
			]
		)
		self.assertEqual(window, ["2026-08-14", "2026-09-14"])
		self.assertEqual(result["row_errors"], [])

	def test_a_run_90_days_ago_caps_at_62_days_and_names_the_unread_dates(self):
		window, result = self.window_after([completed_run("SYNC-1", D(2026, 6, 16, 10, 0))])
		self.assertEqual(window, ["2026-07-15", "2026-09-14"])
		(note,) = result["row_errors"]
		self.assertIn("before 2026-07-15 were not read", note)
		self.assertIn("2026-06-16", note)
		self.assertIn("import_missing_checkins for 2026-06-15..2026-07-14", note)
		self.assertIn("dry run first", note)
		self.assertEqual((result["errored"], result["orphaned"], result["contested"]), (0, 0, 0))

	def test_no_completed_run_keeps_14_days_and_says_older_punches_need_the_manual_import(self):
		window, result = self.window_after([completed_run("SYNC-F", D(2026, 9, 1, 10, 0), status="Failed")])
		self.assertEqual(window, ["2026-09-01", "2026-09-14"])
		(note,) = result["row_errors"]
		self.assertIn("before 2026-09-01 were not read", note)
		self.assertIn("no completed sync", note)
		self.assertIn("import_missing_checkins", note)

	def test_the_note_is_recorded_even_when_a_manual_import_holds_the_lock(self):
		site = self.use(FakeSite(employees=["EMP-1"], runs=[completed_run("SYNC-1", D(2026, 6, 16))]))
		site.locked = True
		result = self.run_import(FakeClient([]))
		self.assertTrue(result["outcomes"]["busy"])
		self.assertEqual(len(result["row_errors"]), 1)


class TestAPunchDeletedHereStaysDeleted(_SiteCase):
	"""HR deleted an imported punch on the hub: the source punch is never re-imported."""

	PUNCH = punch("EMP-1", "2026-09-03 08:48:00", "IN", "R-1")

	def import_with(self, deleted):
		self.use(FakeSite(employees=["EMP-1"], deleted=deleted))
		return self.run_import(FakeClient([self.PUNCH]))

	def test_a_deleted_imported_punch_is_refused_deleted_here(self):
		result = self.import_with([deleted_punch("HR-EMP-CHK-1", "nasty-live::R-1")])
		self.assertEqual(self.site.checkins(), {})
		self.assertEqual(result["outcomes"]["refused"], 1)
		self.assertIn("R-1 (deleted_here)", result["outcomes"]["sample"][0])

	def test_a_deleted_local_punch_blocks_nothing(self):
		result = self.import_with(
			[deleted_punch("HR-EMP-CHK-2", None), deleted_punch("HR-EMP-CHK-3", "other-live::R-1")]
		)
		self.assertEqual(
			{row["source_checkin"] for row in self.site.checkins().values()}, {"nasty-live::R-1"}
		)
		self.assertEqual(result["outcomes"]["refused"], 0)

	def test_a_restored_deleted_document_is_not_a_deletion(self):
		result = self.import_with([deleted_punch("HR-EMP-CHK-1", "nasty-live::R-1", restored=1)])
		self.assertEqual(
			{row["source_checkin"] for row in self.site.checkins().values()}, {"nasty-live::R-1"}
		)
		self.assertEqual(result["outcomes"]["refused"], 0)

	def test_the_deleted_lookup_is_one_query_bounded_by_the_window(self):
		self.import_with([deleted_punch("HR-EMP-CHK-1", "nasty-live::R-1")])
		calls = [filters for doctype, filters in self.site.get_all_calls if doctype == "Deleted Document"]
		self.assertEqual(len(calls), 1)
		self.assertEqual(calls[0]["creation"][0], ">=")


# --- the heal: dry run first ------------------------------------------------------


class _WhitelistCase(_SiteCase):
	def use(self, site, punches=()):
		super().use(site)
		self.client = FakeClient(list(punches))
		client_module = types.ModuleType("hrms.sync.client")
		client_module.RemoteInstanceClient = lambda instance: self.client

		class RemoteInstanceError(Exception):
			pass

		client_module.RemoteInstanceError = RemoteInstanceError
		modules = mock.patch.dict(sys.modules, {"hrms.sync.client": client_module})
		modules.start()
		self.addCleanup(modules.stop)
		self.fence = mock.MagicMock()
		fence = mock.patch("hrms.overrides.company_scope.require_unfenced", self.fence)
		fence.start()
		self.addCleanup(fence.stop)
		return site


class TestImportMissingCheckins(_WhitelistCase):
	PUNCHES = (
		punch("EMP-1", "2026-09-03 08:48:00", "IN", "R-1"),
		punch("EMP-1", "2026-09-04 01:04:00", "OUT", "R-2"),
	)

	def site(self):
		return FakeSite(
			employees=["EMP-1"],
			attendance=[
				{
					"name": "HR-ATT-0001",
					"employee": "EMP-1",
					"attendance_date": "2026-09-03",
					"status": "Absent",
					"docstatus": 1,
					"auto_attendance": 1,
				}
			],
		)

	def test_a_dry_run_inserts_nothing_and_lists_what_it_would(self):
		site = self.use(self.site(), self.PUNCHES)
		result = ci.import_missing_checkins(INSTANCE, "2026-09-01", "2026-09-14", dry_run=1)

		self.assertTrue(result["dry_run"])
		self.assertEqual(result["to_insert"], 2)
		self.assertEqual([row["remote_name"] for row in result["inserts"]], ["R-1", "R-2"])
		self.assertEqual(site.checkins(), {})
		self.assertEqual(site.insert_calls, [])

	def test_a_dry_run_names_the_days_that_already_have_attendance(self):
		"""The OUT at 01:04 on the 4th closes the 3rd's shift, so only the 3rd needs
		a look — and it already reads Absent."""
		self.use(self.site(), self.PUNCHES)
		result = ci.import_missing_checkins(INSTANCE, "2026-09-01", "2026-09-14", dry_run=1)

		self.assertEqual(len(result["attendance_days"]), 1)
		day = result["attendance_days"][0]
		self.assertEqual((day["employee"], day["attendance_date"]), ("EMP-1", "2026-09-03"))
		self.assertEqual(
			[(row["name"], row["status"], row["docstatus"]) for row in day["attendance"]],
			[("HR-ATT-0001", "Absent", 1)],
		)

	def test_it_is_gated_to_hr_managers_and_unfenced_callers(self):
		site = self.use(self.site(), self.PUNCHES)
		ci.import_missing_checkins(INSTANCE, "2026-09-01", "2026-09-14", dry_run=1)
		self.assertEqual(site.only_for_calls, [("System Manager", "HR Manager")])
		self.fence.assert_called_once()

	def test_applying_refuses_while_a_sync_of_the_instance_is_running(self):
		site = self.site()
		site.tables["HRMS Sync Run"]["SYNC-00090"] = {
			"name": "SYNC-00090",
			"source_instance": INSTANCE,
			"status": "Running",
			"started_at": datetime.datetime.now(),
		}
		self.use(site, self.PUNCHES)
		with self.assertRaises(Exception) as refused:
			ci.import_missing_checkins(INSTANCE, "2026-09-01", "2026-09-14", dry_run=0)
		self.assertIn("SYNC-00090", str(refused.exception))
		self.assertEqual(site.checkins(), {})

	def test_applying_counts_a_concurrently_imported_punch_as_already_imported(self):
		site = self.use(self.site(), self.PUNCHES)
		site.committed_elsewhere = {"nasty-live::R-1"}
		result = ci.import_missing_checkins(INSTANCE, "2026-09-01", "2026-09-14", dry_run=0)
		self.assertEqual((result["inserted"], result["already_imported"], result["errored"]), (1, 1, 0))
		self.assertEqual({row["source_checkin"] for row in site.checkins().values()}, {"nasty-live::R-2"})

	def test_applying_refuses_while_another_import_holds_the_lock(self):
		site = self.use(self.site(), self.PUNCHES)
		site.locked = True
		with self.assertRaises(Exception):
			ci.import_missing_checkins(INSTANCE, "2026-09-01", "2026-09-14", dry_run=0)
		self.assertEqual(site.checkins(), {})

	def test_a_dry_run_takes_no_lock(self):
		site = self.use(self.site(), self.PUNCHES)
		site.locked = True
		ci.import_missing_checkins(INSTANCE, "2026-09-01", "2026-09-14", dry_run=1)
		self.assertEqual(site.lock_requests, [])

	def test_a_dry_run_refuses_a_punch_deleted_here(self):
		site = self.site()
		site.tables["Deleted Document"]["DEL-1"] = deleted_punch("HR-EMP-CHK-1", "nasty-live::R-1")
		self.use(site, self.PUNCHES)
		result = ci.import_missing_checkins(INSTANCE, "2026-09-01", "2026-09-14", dry_run=1)
		self.assertEqual((result["to_insert"], result["refused"]), (1, 1))
		self.assertEqual(
			[(row["remote_name"], row["reason"]) for row in result["refused_sample"]],
			[("R-1", "deleted_here")],
		)
		applied = ci.import_missing_checkins(INSTANCE, "2026-09-01", "2026-09-14", dry_run=0)
		self.assertEqual({row["source_checkin"] for row in site.checkins().values()}, {"nasty-live::R-2"})
		self.assertEqual(applied["inserted"], 1)

	def test_dry_run_0_inserts_through_the_same_append_only_path(self):
		site = self.use(self.site(), self.PUNCHES)
		result = ci.import_missing_checkins(INSTANCE, "2026-09-01", "2026-09-14", dry_run=0)

		self.assertEqual(result["inserted"], 2)
		self.assertEqual(
			{row["source_checkin"] for row in site.checkins().values()},
			{"nasty-live::R-1", "nasty-live::R-2"},
		)
		again = ci.import_missing_checkins(INSTANCE, "2026-09-01", "2026-09-14", dry_run=0)
		self.assertEqual(again["inserted"], 0, "the heal is as re-runnable as the pull")


class TestRemarkAttendance(_WhitelistCase):
	DAY = "2026-09-03"

	def site(self):
		def att(name, employee, **extra):
			return {
				"name": name,
				"employee": employee,
				"attendance_date": self.DAY,
				"status": "Absent",
				"docstatus": 1,
				"auto_attendance": 1,
				**extra,
			}

		def ck(name, employee, time, log_type, attendance=None):
			return punch(
				employee,
				time,
				log_type,
				name,
				shift="Day",
				shift_start=D(2026, 9, 3, 9, 0),
				attendance=attendance,
			)

		return FakeSite(
			employees=["EMP-1", "EMP-2", "EMP-3", "EMP-4"],
			attendance=[
				att("ATT-1", "EMP-1"),
				att("ATT-2", "EMP-2", auto_attendance=0),
				att("ATT-3", "EMP-3"),
				att("ATT-4", "EMP-4", status="Present"),
			],
			checkins=[
				ck("CK-1", "EMP-1", D(2026, 9, 3, 8, 48), "IN"),
				ck("CK-2", "EMP-1", D(2026, 9, 3, 18, 1), "OUT"),
				ck("CK-3", "EMP-2", D(2026, 9, 3, 8, 48), "IN"),
				ck("CK-4", "EMP-3", D(2026, 9, 3, 8, 48), "IN"),
				ck("CK-5", "EMP-4", D(2026, 9, 3, 8, 48), "IN", attendance="ATT-4"),
			],
		)

	def setUp(self):
		self.use(self.site())
		shift_module = types.ModuleType("hrms.hr.doctype.shift_type.shift_type")
		shift_module.CHECKIN_FIELDS = (
			"name",
			"employee",
			"log_type",
			"time",
			"shift",
			"shift_start",
			"attendance",
		)
		modules = mock.patch.dict(sys.modules, {"hrms.hr.doctype.shift_type.shift_type": shift_module})
		modules.start()
		self.addCleanup(modules.stop)
		self.lock_calls = []

		def locked(employee, day, attendance, for_update):
			self.lock_calls.append((employee, for_update))
			return "SAL-SLIP-0009" if employee == "EMP-3" else None

		lock = mock.patch.object(ci, "_financially_locked", locked)
		lock.start()
		self.addCleanup(lock.stop)

	DAYS = json.dumps([["EMP-1", DAY], ["EMP-2", DAY], ["EMP-3", DAY], ["EMP-4", DAY]])

	def test_a_dry_run_marks_nothing_and_says_what_it_would_do(self):
		result = ci.remark_attendance(self.DAYS, dry_run=1)

		actions = {row["employee"]: row["action"] for row in result["days"]}
		self.assertEqual(
			actions, {"EMP-1": "remark", "EMP-2": "hr-owned", "EMP-3": "locked", "EMP-4": "up-to-date"}
		)
		self.assertEqual(self.site.shift.calls, [])
		self.assertTrue(all(for_update is False for _, for_update in self.lock_calls))
		remark = next(row for row in result["days"] if row["employee"] == "EMP-1")
		(expected,) = remark["expected"]
		self.assertEqual((expected["status"], expected["rebuilds"]), ("Present", "ATT-1"))
		self.assertEqual(expected["out_time"], "2026-09-04 01:04:00")
		self.assertEqual(self.site.shift.previews, [("EMP-1", datetime.date(2026, 9, 3), ["CK-1", "CK-2"])])

	def test_apply_re_marks_exactly_the_days_asked_through_the_shift_rule(self):
		result = ci.remark_attendance(self.DAYS, dry_run=0)

		self.assertEqual(self.site.shift.calls, [("EMP-1", datetime.date(2026, 9, 3), ["CK-1", "CK-2"])])
		self.assertEqual(self.site.db.deletes, [])
		remarked = next(row for row in result["days"] if row["employee"] == "EMP-1")
		self.assertEqual(remarked["marked"], ["HR-ATT-NEW"])

	def test_employee_days_accepts_pairs_and_dicts(self):
		self.assertEqual(
			ci.parse_employee_days(
				[["EMP-1", "2026-09-03"], {"employee": "EMP-2", "attendance_date": "2026-09-04"}]
			),
			[("EMP-1", datetime.date(2026, 9, 3)), ("EMP-2", datetime.date(2026, 9, 4))],
		)

	def test_a_non_string_employee_is_refused_so_it_never_becomes_a_filter_operator(self):
		with self.assertRaises(ValueError):
			ci.parse_employee_days([{"employee": ["like", "%"], "attendance_date": "2026-09-03"}])
		with self.assertRaises(ValueError):
			ci.parse_employee_days([[["like", "%"], "2026-09-03"]])


if __name__ == "__main__":
	unittest.main()
