"""Bench probe for the HR Fix Day screen: the 7:30PM-3:30AM shape, and a paid day.

Two things the unit tests cannot show, because they need the real engine and a
real site:

1. THE SHAPE. A night shift 19:30-03:30 whose closing tap was stamped as the
   NEXT shift's IN (the defect class behind the 7:30PM-3:30AM days). The probe
   marks both days as they stand, prints the day, pairs the two taps through
   `hrms.api.attendance_fix_day.pair_taps`, and prints the day again with hours
   and OT as the engine recomputed them. HR typed neither figure.
2. THE REFUSALS. A day carrying approved overtime: all five actions are asked
   for and each must come back with a plain sentence naming the reason.

Run on a bench site, from `bench --site fresh.local console`:

    import sys, hrms, frappe
    WT = "/path/to/worktree"
    hrms.__path__.insert(0, WT + "/hrms")
    [sys.modules.pop(k) for k in [k for k in list(sys.modules) if k.startswith("hrms.")]]
    frappe.controllers = {}
    exec(open(WT + "/hrms/tests/probes/fix_day_probe.py").read(), globals())
    run()

Everything it creates sits under a savepoint and is rolled back at the end;
nothing is committed. Fixture names all start with `fdp_` / `FDP `.

The HR Day Fix Log doctype ships with this change and is not migrated on a site
that has not run `bench migrate` yet, so the probe replaces the log seam with a
list and says so in its output. Nothing else is stubbed: the guards, the writes
and the re-mark are the real ones.
"""

import traceback
from datetime import datetime, time, timedelta

import frappe
from frappe.utils import getdate

SAVEPOINT = "fix_day_probe"
NIGHT = "FDP Night 7:30PM-3:30AM"
MORNING = "FDP Morning 7:30AM-4:30PM"
DAY_SHIFT = "FDP Day 9AM-6PM"
DAY = getdate("2026-09-02")
NEXT = getdate("2026-09-03")
PAID_DAY = getdate("2026-09-08")
#: the shift's own window must cover the probe's dates or the engine marks nothing
PROCESS_AFTER = "2026-08-01"
LAST_SYNC = "2026-09-30 23:59:59"
LINES = []
LOGGED = []


def say(text=""):
	LINES.append(str(text))


def at(day, clock):
	return datetime.combine(getdate(day), time.fromisoformat(clock))


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
def _company():
	return frappe.db.get_value("Company", {}, "name")


def _employee(tag):
	doc = frappe.get_doc(
		{
			"doctype": "Employee",
			"first_name": f"fdp_{tag}",
			"company": _company(),
			"date_of_birth": "1990-01-01",
			"date_of_joining": "2020-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name"),
			"status": "Active",
		}
	)
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	return doc.name


def _shift(name, start, end):
	"""A shift the engine will actually mark: auto attendance on, and its
	window (process_attendance_after .. last_sync_of_checkin) over the probe's
	dates — `ShiftType.has_incorrect_shift_config` refuses it otherwise."""
	if frappe.db.exists("Shift Type", name):
		return name
	doc = frappe.get_doc(
		{
			"doctype": "Shift Type",
			"__newname": name,
			"start_time": start,
			"end_time": end,
			"enable_auto_attendance": 1,
			"process_attendance_after": PROCESS_AFTER,
			"last_sync_of_checkin": LAST_SYNC,
			"determine_check_in_and_check_out": "Alternating entries as IN and OUT during the same shift",
			"working_hours_calculation_based_on": "First Check-in and Last Check-out",
			"enable_overtime": 1,
			"minimum_overtime_minutes": 0,
			"working_hours_threshold_for_absent": 0,
			"working_hours_threshold_for_half_day": 0,
		}
	)
	doc.flags.ignore_mandatory = True
	doc.insert(ignore_permissions=True)
	return name


def _assign(employee, shift, start, end):
	doc = frappe.get_doc(
		{
			"doctype": "Shift Assignment",
			"employee": employee,
			"company": frappe.db.get_value("Employee", employee, "company"),
			"shift_type": shift,
			"start_date": start,
			"end_date": end,
			"status": "Active",
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc.name


def _tap(employee, moment, log_type, shift, shift_start, shift_end):
	doc = frappe.get_doc(
		{
			"doctype": "Employee Checkin",
			"employee": employee,
			"time": moment,
			"log_type": log_type,
			"shift": shift,
			"shift_start": shift_start,
			"shift_end": shift_end,
			"shift_actual_start": shift_start,
			"shift_actual_end": shift_end,
			"device_id": "FDP door",
		}
	)
	doc.flags.ignore_validate = True
	doc.flags.ignore_permissions = True
	doc.flags.skip_session_restamp = True
	doc.insert()
	return doc.name


def _approved_overtime(employee, day, hours):
	doc = frappe.get_doc(
		{
			"doctype": "OT Request",
			"employee": employee,
			"company": frappe.db.get_value("Employee", employee, "company"),
			"ot_date": day,
			"claimed_hours": hours,
			"status": "Approved",
		}
	)
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_permissions = True
	doc.insert()
	doc.submit()
	return doc.name


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #
def _day_line(fd, employee, day):
	screen = fd.get_day(employee, str(day))
	for row in screen["attendance"] or [{}]:
		say(
			f"    {day}: status={row.get('status')} in={row.get('in_time')} out={row.get('out_time')} "
			f"hours={row.get('hours')} OT={row.get('overtime')}"
		)
	for tap in screen["taps"]:
		say(f"      tap {tap['name']} {tap['time']} {tap['log_type']} shift={tap['shift']} [{tap['state']}]")
	if screen["blocked"]:
		say(f"      BLOCKED: {screen['blocked']}")
	return screen


def _remark(employee, day):
	from hrms.utils.day_remark import remark_day

	return remark_day(employee, day, "fix day probe setup")


# --------------------------------------------------------------------------- #
# the two scenarios
# --------------------------------------------------------------------------- #
def _shape(fd):
	say("## 1. The 7:30PM-3:30AM shape: the closing tap read as the next shift's IN")
	employee = _employee("night")
	_shift(NIGHT, "19:30:00", "03:30:00")
	_shift(MORNING, "07:30:00", "16:30:00")
	_assign(employee, NIGHT, DAY, DAY)
	_assign(employee, MORNING, NEXT, NEXT)
	first = _tap(employee, at(DAY, "19:30"), "IN", NIGHT, at(DAY, "19:30"), at(NEXT, "03:30"))
	second = _tap(employee, at(NEXT, "03:30"), "IN", MORNING, at(NEXT, "07:30"), at(NEXT, "16:30"))
	say(f"  employee={employee}")
	say(f"  taps: {first} IN 19:30 on {NIGHT} · {second} IN 03:30 on {MORNING}")
	say(f"  pairing rule: {frappe.db.get_value('Shift Type', NIGHT, 'determine_check_in_and_check_out')}")
	for day in (DAY, NEXT):
		answer = _remark(employee, day)
		say(f"  re-mark {day} as it stands: marked={answer.get('marked')} errors={answer.get('errors')}")
	say("  BEFORE:")
	_day_line(fd, employee, DAY)
	_day_line(fd, employee, NEXT)

	answer = fd.pair_taps(first, second, reason="the 03:30 tap closes the night shift; it is not a new IN")
	say(f"  pair_taps -> ok={answer['ok']} log={answer['log']}")
	for day, result in answer["rebuild"].items():
		say(f"    re-mark {day}: marked={result.get('marked')} errors={result.get('errors')}")
	say("  AFTER:")
	_day_line(fd, employee, DAY)
	_day_line(fd, employee, NEXT)
	say("  the hours and the OT above were recomputed by the engine; HR typed neither.")
	say()
	return employee


def _paid_day_refuses_everything(fd):
	say("## 2. A day with approved overtime: every action refused")
	employee = _employee("paid")
	_shift(DAY_SHIFT, "09:00:00", "18:00:00")
	_assign(employee, DAY_SHIFT, PAID_DAY, PAID_DAY)
	window = (at(PAID_DAY, "09:00"), at(PAID_DAY, "18:00"))
	tap_in = _tap(employee, at(PAID_DAY, "09:00"), "IN", DAY_SHIFT, *window)
	tap_out = _tap(employee, at(PAID_DAY, "20:00"), "OUT", DAY_SHIFT, *window)
	answer = _remark(employee, PAID_DAY)
	say(f"  employee={employee} day={PAID_DAY} (IN 09:00, OUT 20:00)")
	say(f"  re-mark: marked={answer.get('marked')} errors={answer.get('errors')}")

	from hrms.utils.ot_calculation import get_ot_claim_capacity

	proven = get_ot_claim_capacity(employee, PAID_DAY, "Overtime Pay")["hours"]
	say(f"  overtime the punches prove: {proven} h")
	if proven <= 0:
		say("  cannot build an approved OT claim on this day; the refusals below would not be about payout")
		return
	overtime = _approved_overtime(employee, PAID_DAY, round(float(proven), 2))
	say(f"  approved overtime: {overtime}")
	attempts = (
		("pair_taps", lambda: fd.pair_taps(tap_in, tap_out, reason="probe")),
		("move_tap", lambda: fd.move_tap(tap_in, shift=MORNING, reason="probe")),
		("ignore_tap", lambda: fd.ignore_tap(tap_in, reason="probe")),
		("restore_tap", lambda: fd.restore_tap(tap_in, reason="probe")),
		("add_tap", lambda: fd.add_tap(employee, str(at(PAID_DAY, "23:00")), "OUT", reason="probe")),
	)
	for name, call in attempts:
		try:
			call()
			say(f"    {name}: NOT REFUSED — the guard let it through")
		except Exception as exc:
			say(f"    {name}: REFUSED — {exc}")
	say()


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def run(path=None):
	from hrms.api import attendance_fix_day as fd

	LINES.clear()
	LOGGED.clear()
	frappe.set_user("Administrator")
	real_log = fd._write_log

	def fake_log(fields):
		LOGGED.append(fields)
		return f"HRFIX-PROBE-{len(LOGGED):05d}"

	fd._write_log = fake_log
	frappe.db.savepoint(SAVEPOINT)
	say("# HR Fix Day probe")
	say(f"site={frappe.local.site} company={_company()}")
	say("(HR Day Fix Log is not migrated on this site; the log seam records to a list)")
	say()
	try:
		_shape(fd)
		_paid_day_refuses_everything(fd)
		say(f"fix log entries written: {len(LOGGED)} -> {[e['action'] for e in LOGGED]}")
	except Exception:
		say("PROBE ERROR")
		say(traceback.format_exc())
	finally:
		fd._write_log = real_log
		frappe.db.rollback(save_point=SAVEPOINT)
		say("rolled back: nothing committed")
	report = "\n".join(LINES)
	if path:
		with open(path, "w") as handle:
			handle.write(report)
	print(report)
	return report
