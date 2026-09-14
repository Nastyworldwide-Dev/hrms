"""Shift Attendance master edit — HR fixes a day like a spreadsheet, and it sticks.

Owner requirement, 14 Sep 2026: HR (HR User, HR Manager, System Manager) edits
any cell of the Shift Attendance report — date, shift, in time, out time,
status — bulk edits, removes a row, adds a missing row, adds or changes a
shift. No automation may overwrite that edit and no two writers may clash.

How the edit is made to stick, using ownership rules that already exist:

* The saved Attendance is `auto_attendance = 0`. The hourly job never rebuilds
  such a row (shift_type.get_automation_attendance), the ERP-import re-mark
  refuses it (checkin_import.plan_remark), the late-checkout repair refuses a
  "manually maintained" row, and a later punch on the day is linked to it as
  evidence (employee_checkin._link_to_hr_row).
* HR's in and out are punches of HR's own (device_id HR_DEVICE), linked to
  that row. An original device / PWA / import punch is never re-timed and its
  approval state never changed: it is skip-stamped with a comment carrying
  SKIP_MARKER, so a Pending out-of-area punch never becomes effective.
* Hours, late/early and — when HR changed times but sent no status — the
  status come from the hourly job's own day rule (ShiftType.get_attendance):
  pairing, unpaid early arrival, unpaid breaks, thresholds.
* A removed day always gets one HR_REMOVED_DEVICE marker punch
  (hrms.utils.hr_removed_day). Every automation path honours it: the Absent
  sweep, the hourly marking (which holds later punches), the ERP-import
  re-mark, the off-shift heal, the late-checkout repair and recovery.
* `hand_back` undoes the ownership: it cancels HR's row, clears only the skip
  stamps this module wrote, deletes HR's punches and the marker, and queues
  the engine.

Known race (W7, G2-G4 review, documented not fixed): the Employee row lock
serializes HR edits, but the hourly job does not take it. When HR moves a day
to a shift that does not overlap the old one, a job run for the OLD shift that
read the day's punches before HR's save can still mark a row under the old
shift after it — Attendance's duplicate check is per overlapping shift, so both
rows stand. The day then shows two rows and the editor refuses it as
"multiple_rows" until HR cancels one in Desk.
# ceiling: no lock shared with the hourly job, upgrade: take a per-employee
# named lock in mark_attendance_for_shift_logs if two-row days are reported

Clash protection: every row carries the `revision` its screen was built from
(`get_day`). A day that changed since then is refused with the current day,
never overwritten. The Employee row is locked for the edit so two HR users
saving the same person queue behind each other.

Overtime: the new Attendance's own validate runs `set_overtime` from the HR
punches — the same engine `recompute_ot_backfill` calls. The backfill itself
is deliberately NOT called: it re-prices every employee's attendance on the
date (other companies included, past the caller's fence) and commits per
batch, which would break the per-row savepoint.
"""

import hashlib
import html
import json
import logging
import re
from datetime import datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, get_time, getdate, now_datetime

from hrms.hr.doctype.attendance.attendance import validate_attendance_times
from hrms.hr.doctype.shift_assignment.shift_assignment import MultipleShiftError, OverlappingShiftError
from hrms.overrides import company_scope
from hrms.utils.hr_removed_day import HR_REMOVED_DEVICE, SKIP_MARKER
from hrms.utils.offshift_punch_heal import _lost_transaction

logger = logging.getLogger(__name__)

HR_ROLES = ("HR User", "HR Manager", "System Manager")
MAX_ROWS = 200
#: days one get_days call may read (the report shows at most this many rows)
MAX_DAYS = 500
ACTIONS = ("edit", "add", "remove")
EDITABLE = frozenset(("status", "shift", "in_time", "out_time", "attendance_date"))
STATUSES = ("Present", "Absent", "Half Day", "Work From Home")
#: device_id of a punch HR typed through this editor
HR_DEVICE = "HR master edit"
ROW_SAVEPOINT = "attendance_master_edit_row"
_CLOCK = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")

ATTENDANCE_FIELDS = [
	"name",
	"employee",
	"attendance_date",
	"status",
	"docstatus",
	"shift",
	"in_time",
	"out_time",
	"working_hours",
	"late_entry",
	"early_exit",
	"auto_attendance",
	"leave_type",
	"modify_half_day_status",
	"synced_from_instance",
	"ot_hours",
	"modified",
]
PUNCH_FIELDS = [
	"name",
	"employee",
	"time",
	"log_type",
	"shift",
	"shift_start",
	"attendance",
	"skip_auto_attendance",
	"device_id",
	"synced_from_instance",
	"remote_approval_status",
	"modified",
]
ASSIGNMENT_FIELDS = ["name", "shift_type", "start_date", "end_date", "synced_from_instance", "modified"]


class RowRefused(Exception):
	"""One row cannot be saved; the reason goes back to HR, the batch goes on."""

	def __init__(self, code: str, message: str, current: dict | None = None):
		super().__init__(message)
		self.code, self.message, self.current = code, message, current

	def as_result(self) -> dict:
		result = {
			"ok": False,
			"conflict": self.code == "conflict",
			"code": self.code,
			"error": self.message,
			"attendance": None,
			"revision": self.current["revision"] if self.current else None,
		}
		if self.current is not None:
			result["current"] = self.current
		return result


# --- endpoints ----------------------------------------------------------------


@frappe.whitelist(methods=["POST"])
def get_day(employee: str, attendance_date: str) -> dict:
	"""The day as the editor shows it, with the revision a save must carry."""
	_require_hr()
	try:
		day = _parse_day(attendance_date)
		emp = _require_employee(employee, lock=False)
	except RowRefused as refusal:
		exc = {"fenced": frappe.PermissionError, "not_found": frappe.DoesNotExistError}.get(
			refusal.code, frappe.ValidationError
		)
		frappe.throw(refusal.message, exc)
	return _snapshot(emp, day)


@frappe.whitelist(methods=["POST"])
def get_days(employee_dates) -> dict:
	"""Revisions for many days at once, so the grid holds them from the moment
	the report loads. `employee_dates`: [{employee, attendance_date}], at most
	MAX_DAYS. A day the caller may not see, or cannot parse, comes back with
	`revision` None and an `error` — never another company's data."""
	_require_hr()
	employee_dates = parse_rows(employee_dates, limit=MAX_DAYS)
	days, employees = {}, {}
	for item in employee_dates:
		raw = item if isinstance(item, dict) else {}
		employee, attendance_date = raw.get("employee"), raw.get("attendance_date")
		key = f"{employee}|{attendance_date}"
		if key in days:
			continue
		try:
			day = _parse_day(attendance_date)
			if employee not in employees:
				employees[employee] = _require_employee(str(employee or "").strip(), lock=False)
			snap = _snapshot(employees[employee], day)
			days[key] = {"revision": snap["revision"], "day": snap}
		except RowRefused as refusal:
			employees.pop(employee, None)
			days[key] = {"revision": None, "error": refusal.message, "code": refusal.code}
	logger.info("[attendance_master_edit] %s read %d day(s)", frappe.session.user, len(days))
	return {"days": days}


@frappe.whitelist(methods=["POST"])
def save_rows(rows) -> dict:
	"""Save each row in its own savepoint; one bad row never blocks the rest."""
	_require_hr()
	rows = parse_rows(rows)
	is_sm = _is_system_manager()
	results = []
	for index, row in enumerate(rows):
		frappe.db.savepoint(ROW_SAVEPOINT)
		try:
			result = _save_row(row, is_sm)
		except RowRefused as refusal:
			frappe.db.rollback(save_point=ROW_SAVEPOINT)
			result = refusal.as_result()
			logger.info(
				"[attendance_master_edit] row %d refused: %s %s", index, refusal.code, refusal.message
			)
		except Exception as exc:
			if _lost_transaction(exc):
				# the transaction is gone: rows reported saved above would be a lie
				raise
			frappe.db.rollback(save_point=ROW_SAVEPOINT)
			logger.exception("[attendance_master_edit] row %d failed; rolled back", index)
			result = {
				"ok": False,
				"conflict": False,
				"code": "error",
				"error": str(exc),
				"attendance": None,
				"revision": None,
			}
		frappe.clear_messages()
		raw = row if isinstance(row, dict) else {}
		results.append(
			{
				"index": index,
				"employee": raw.get("employee"),
				"attendance_date": raw.get("attendance_date"),
				**result,
			}
		)
	saved = sum(1 for r in results if r["ok"])
	logger.info("[attendance_master_edit] %s saved %d of %d row(s)", frappe.session.user, saved, len(results))
	return {"rows": results, "saved": saved, "refused": len(results) - saved}


@frappe.whitelist(methods=["POST"])
def hand_back(employee: str, attendance_date: str, revision: str) -> dict:
	"""Let automation manage the day again."""
	_require_hr()
	is_sm = _is_system_manager()
	frappe.db.savepoint(ROW_SAVEPOINT)
	try:
		return _hand_back(employee, attendance_date, revision, is_sm)
	except RowRefused as refusal:
		frappe.db.rollback(save_point=ROW_SAVEPOINT)
		logger.info("[attendance_master_edit] hand back refused: %s", refusal.code)
		return refusal.as_result()
	except Exception as exc:
		if not _lost_transaction(exc):
			frappe.db.rollback(save_point=ROW_SAVEPOINT)
		raise


# --- row flow -------------------------------------------------------------------


def _save_row(row, is_sm: bool) -> dict:
	employee, day, action, changes, revision = normalize_row(row)
	emp = _require_employee(employee, lock=True)
	if day > _today():
		raise RowRefused("invalid", _("Attendance cannot be saved for a future date."))
	snap = _snapshot(emp, day)
	if revision != snap["revision"]:
		raise RowRefused(
			"conflict", _("This day changed since you opened it. Review it and save again."), current=snap
		)

	new_day = changes.pop("attendance_date", None)
	new_day = _parse_day(new_day) if new_day else None
	if new_day == day:
		new_day = None

	if action == "remove":
		if new_day:
			raise RowRefused("invalid", _("A removed row has no new date."))
		_remove(emp, day, snap, is_sm)
		name, final_day = None, day
	elif new_day:
		name, final_day = _move(emp, day, new_day, changes, snap, is_sm), new_day
	else:
		if action == "add" and any(cint(r.docstatus) == 1 for r in snap["attendance"]):
			raise RowRefused("target_day_taken", _("This day already has attendance; edit it instead."))
		name, final_day = _edit(emp, day, changes, snap, is_sm), day

	logger.info("[attendance_master_edit] %s %s on %s -> %s", action, employee, day, name)
	return {
		"ok": True,
		"conflict": False,
		"code": None,
		"error": None,
		"attendance": name,
		"attendance_date": str(final_day),
		"revision": _snapshot(emp, final_day)["revision"],
	}


def _edit(emp, day, changes, snap, is_sm, replaces=None) -> str:
	"""Write HR's values for the day: punches first, then an HR-owned row."""
	target = owned_target(snap["attendance"], snap["punches"])
	values = resolve_values(target, changes, day, fallback_shift(snap, emp))
	_refuse_if_paid(emp.name, day, target, is_sm)
	if values.shift:
		_ensure_assignment(emp, day, values.shift, snap["assignments"])
	if target:
		# cancel first: Attendance.on_cancel unlinks the punches, and a linked
		# punch's time cannot be changed (EmployeeCheckin.validate_time_change)
		_cancel_attendance(target.name)

	window = _shift_window(values.shift, day) if values.shift else None
	linked = _set_punches(emp, day, values, snap["punches"], window)

	hours, late, early = 0, False, False
	if values.in_time and values.out_time:
		shift_doc = _shift_doc(values.shift)
		result = engine_day(
			shift_doc,
			emp.name,
			window,
			values.in_time,
			values.out_time,
			half_holiday=_is_half_holiday(shift_doc, emp.name, day),
		)
		hours, late, early = result.working_hours, result.late_entry, result.early_exit
		if values.derive_status:
			values.status = result.status
	saved = _insert_attendance(
		{
			"employee": emp.name,
			"company": emp.company,
			"attendance_date": day,
			"status": values.status,
			"shift": values.shift,
			"in_time": values.in_time,
			"out_time": values.out_time,
			"working_hours": hours,
			"late_entry": late,
			"early_exit": early,
			"auto_attendance": 0,
		}
	)
	if linked:
		_link_punches(linked, saved.name)

	before = replaces or target
	text = _("Edited by {0} via Shift Attendance: {1}").format(
		frappe.session.user, "; ".join(describe_changes(before, values)) or _("no field changed")
	)
	if before:
		text += " " + _("(replaces {0})").format(before.name)
	_comment("Attendance", saved.name, text)
	logger.info(
		"[attendance_master_edit] %s on %s saved as HR-owned %s: %s %sh",
		emp.name,
		day,
		saved.name,
		saved.status,
		saved.working_hours,
	)
	return saved.name


def _remove(emp, day, snap, is_sm) -> None:
	"""Cancel the day and keep automation from marking it again."""
	target = owned_target(snap["attendance"], snap["punches"])
	live = [p for p in snap["punches"] if not cint(p.skip_auto_attendance)]
	marked = any(p.device_id == HR_REMOVED_DEVICE for p in snap["punches"])
	if not target and not live:
		raise RowRefused("nothing_to_remove", _("There is no attendance on this day to remove."))
	_refuse_if_paid(emp.name, day, target, is_sm)
	user = frappe.session.user
	if target:
		_cancel_attendance(target.name)
		_comment("Attendance", target.name, _("Removed by {0} via Shift Attendance.").format(user))
	for punch in live:
		_set_skip(punch.name, 1)
		_comment(
			"Employee Checkin",
			punch.name,
			f"{SKIP_MARKER} " + _("Day removed by {0} via Shift Attendance.").format(user),
		)
	if not marked:
		# The durable "removed by HR" marker (hrms.utils.hr_removed_day): without
		# it a day whose punches are all Rejected, or one a later punch reaches,
		# is marked again within the hour (G2-G4 review C1).
		shift = (target.shift if target else None) or fallback_shift(snap, emp)
		window = _shift_window(shift, day) if shift else None
		fields = {
			"employee": emp.name,
			"time": window.start_datetime if window else datetime.combine(day, time()),
			"log_type": None,
			"device_id": HR_REMOVED_DEVICE,
			**(punch_stamp(shift, window) if window else {}),
			"skip_auto_attendance": 1,
		}
		name = _insert_punch(fields)
		_comment(
			"Employee Checkin",
			name,
			_("Marker: the day {0} was removed by {1}; automation does not mark it again.").format(day, user),
		)
	logger.info("[attendance_master_edit] %s on %s removed (row %s)", emp.name, day, target and target.name)


def _move(emp, day, new_day, changes, snap, is_sm) -> str:
	"""A date change is remove-old-day plus add-new-day, inside one savepoint."""
	if new_day > _today():
		raise RowRefused("invalid", _("Attendance cannot be moved to a future date."))
	target = owned_target(snap["attendance"], snap["punches"])
	if _snapshot(emp, new_day)["attendance"]:
		raise RowRefused(
			"target_day_taken",
			_("{0} already has attendance on {1}; edit that day instead.").format(emp.name, new_day),
		)
	carried = carry_to(target, changes, day, new_day)
	_remove(emp, day, snap, is_sm)
	logger.info("[attendance_master_edit] %s moving %s -> %s", emp.name, day, new_day)
	return _edit(emp, new_day, carried, _snapshot(emp, new_day), is_sm, replaces=target)


def _hand_back(employee, attendance_date, revision, is_sm) -> dict:
	day = _parse_day(attendance_date)
	emp = _require_employee(employee, lock=True)
	snap = _snapshot(emp, day)
	if revision != snap["revision"]:
		raise RowRefused(
			"conflict", _("This day changed since you opened it. Review it and try again."), current=snap
		)
	target = owned_target(snap["attendance"], snap["punches"])
	if target and cint(target.auto_attendance):
		raise RowRefused("not_hr_owned", _("Automation already manages this day."))
	# ceiling: a punch skip-stamped here, handed back and later skip-stamped by
	# something else still carries the old marker; Rejected punches are excluded,
	# upgrade: a release marker per hand back if another skip writer appears
	skipped = [
		p.name
		for p in snap["punches"]
		if cint(p.skip_auto_attendance)
		and p.device_id != HR_REMOVED_DEVICE
		and p.remote_approval_status != "Rejected"
	]
	released = sorted(_skip_marked(skipped)) if skipped else []
	markers = [p for p in snap["punches"] if p.device_id in (HR_REMOVED_DEVICE, HR_DEVICE)]
	if not (target or released or markers):
		raise RowRefused("nothing_to_hand_back", _("Nothing on this day was set by the attendance editor."))
	_refuse_if_paid(emp.name, day, target, is_sm)

	user = frappe.session.user
	if target:
		_cancel_attendance(target.name)
		_comment("Attendance", target.name, _("Handed back to automation by {0}.").format(user))
	for name in released:
		_set_skip(name, 0)
		_comment("Employee Checkin", name, _("Handed back to automation by {0}.").format(user))
	for marker in markers:
		_delete_punch(marker.name)

	shift = (target.shift if target else None) or next(
		(p.shift for p in snap["punches"] if p.shift and p.device_id not in (HR_DEVICE, HR_REMOVED_DEVICE)),
		next((p.shift for p in snap["punches"] if p.shift), None),
	)
	# today is the hourly job's to mark once the shift ends
	enqueued = bool(shift and day < _today())
	if enqueued:
		_enqueue_engine(shift)
	logger.info(
		"[attendance_master_edit] %s handed back %s on %s: row=%s released=%d enqueued=%s",
		user,
		emp.name,
		day,
		target and target.name,
		len(released),
		enqueued,
	)
	return {
		"ok": True,
		"conflict": False,
		"code": None,
		"error": None,
		"attendance": None,
		"cancelled": target.name if target else None,
		"released_punches": released,
		"enqueued": enqueued,
		"revision": _snapshot(emp, day)["revision"],
	}


def _refuse_if_paid(employee, day, target, is_sm) -> None:
	dependency = _financial_dependency(employee, day, target.name if target else None)
	if not dependency:
		return
	if not is_sm:
		raise RowRefused(
			"financial_lock",
			_("{0} already depends on this day. A System Manager must make this change.").format(dependency),
		)
	logger.warning(
		"[attendance_master_edit] System Manager %s changes %s on %s despite %s",
		frappe.session.user,
		employee,
		day,
		dependency,
	)


def _ensure_assignment(emp, day, shift, assignments) -> str | None:
	"""A one-day Shift Assignment when nothing covers the day with this shift."""
	if any(a.shift_type == shift for a in assignments):
		return None
	if not assignments and emp.default_shift == shift:
		return None
	try:
		name = _submit_assignment(
			{
				"employee": emp.name,
				"company": emp.company,
				"shift_type": shift,
				"start_date": day,
				"end_date": day,
				"status": "Active",
			}
		)
	except (OverlappingShiftError, MultipleShiftError):
		others = ", ".join(f"{a.name} ({a.shift_type})" for a in assignments) or _("another assignment")
		raise RowRefused(
			"shift_overlap",
			_(
				"{0} cannot be given on {1}: {2} already covers this day. "
				"An HR Manager must end that assignment first, then save again."
			).format(shift, day, others),
		) from None
	_comment(
		"Shift Assignment",
		name,
		_("One-day assignment created by {0} via Shift Attendance.").format(frappe.session.user),
	)
	logger.info("[attendance_master_edit] one-day %s assignment %s for %s on %s", shift, name, emp.name, day)
	return name


def _set_punches(emp, day, values, punches, window) -> list:
	"""HR's in and out as HR punches; every original punch is left as it was
	recorded and only skip-stamped. Returns the names to link."""
	for marker in (p for p in punches if p.device_id == HR_REMOVED_DEVICE):
		_delete_punch(marker.name)
	own, superseded = plan_punches(punches)
	stamp = punch_stamp(values.shift, window) if window else {}
	linked = []
	for moment, log_type in ((values.in_time, "IN"), (values.out_time, "OUT")):
		existing = own.pop(log_type, None)
		if not moment:
			if existing:
				_delete_punch(existing.name)
			continue
		fields = {"time": moment, "log_type": log_type, **stamp}
		if existing:
			# HR's own earlier punch: re-timing it changes no recorded evidence
			_update_punch(existing.name, fields)
			linked.append(existing.name)
		else:
			linked.append(_insert_punch({"employee": emp.name, "device_id": HR_DEVICE, **fields}))
	for extra in own.get("extra", []):
		_delete_punch(extra.name)
	for punch in superseded:
		_set_skip(punch.name, 1)
		_comment(
			"Employee Checkin",
			punch.name,
			f"{SKIP_MARKER} "
			+ _("Superseded by {0}'s Shift Attendance edit of {1}.").format(frappe.session.user, day),
		)
	logger.debug(
		"[attendance_master_edit] %s on %s: linked %s, superseded %d",
		emp.name,
		day,
		linked,
		len(superseded),
	)
	return linked


# --- pure rules -------------------------------------------------------------------


def parse_rows(rows, limit=MAX_ROWS) -> list:
	if isinstance(rows, str):
		try:
			rows = json.loads(rows)
		except ValueError:
			frappe.throw(_("Rows must be a JSON list."))
	if not isinstance(rows, list):
		frappe.throw(_("Rows must be a list."))
	if len(rows) > limit:
		frappe.throw(_("{0} rows in one call; send at most {1}.").format(len(rows), limit))
	return rows


def normalize_row(row) -> tuple:
	if not isinstance(row, dict):
		raise RowRefused("invalid", _("Each row must be an object."))
	employee = str(row.get("employee") or "").strip()
	action = row.get("action") or "edit"
	changes = row.get("changes") or {}
	revision = row.get("revision")
	if not employee:
		raise RowRefused("invalid", _("The row has no employee."))
	if action not in ACTIONS:
		raise RowRefused("invalid", _("Unknown action {0}.").format(action))
	if not isinstance(changes, dict) or set(changes) - EDITABLE:
		raise RowRefused("invalid", _("Only status, shift, in time, out time and date can be edited."))
	if not revision:
		raise RowRefused("invalid", _("The row has no revision; reload the day."))
	return employee, _parse_day(row.get("attendance_date")), action, dict(changes), str(revision)


def _parse_day(value):
	try:
		if not value:
			raise ValueError(value)
		return getdate(value)
	except Exception:
		raise RowRefused("invalid", _("{0} is not a date.").format(value)) from None


def parse_moment(value, day, after=None):
	"""A typed clock ("09:00") on `day`, or a full datetime. A clock at or
	before `after` is the next morning (a night shift's out)."""
	if value in (None, ""):
		return None
	text = str(value).strip() if not isinstance(value, datetime) else None
	if text is not None and _CLOCK.match(text):
		moment = datetime.combine(day, get_time(text))
		if after and moment <= after:
			moment += timedelta(days=1)
		return moment
	return get_datetime(value)


def resolve_values(current, changes, day, fallback_shift=None):
	"""The day HR asked for: changed cells over the current row. Raises RowRefused."""
	current = current or {}

	def pick(key):
		return changes[key] if key in changes else current.get(key)

	shift = pick("shift") or fallback_shift
	status = pick("status")
	try:
		in_time = parse_moment(pick("in_time"), day)
		out_time = parse_moment(pick("out_time"), day, after=in_time)
	except Exception:
		raise RowRefused("invalid", _("In and out must be times like 09:00.")) from None
	# W1: changed times with no status sent take the engine's status (set in
	# _edit from engine_day). Work From Home is a decision, not a measurement.
	times_changed = "in_time" in changes or "out_time" in changes
	derive = bool(
		in_time
		and out_time
		and "status" not in changes
		and (times_changed or not status)
		and status != "Work From Home"
	)
	if derive:
		status = status or "Present"
	if status not in STATUSES:
		raise RowRefused("invalid", _("Status must be one of {0}.").format(", ".join(STATUSES)))
	try:
		validate_attendance_times(in_time, out_time, day)
	except frappe.ValidationError as exc:
		raise RowRefused("invalid", str(exc)) from None
	if (in_time or out_time) and not shift:
		raise RowRefused("no_shift", _("Choose a shift for a day with in and out times."))
	return frappe._dict(
		status=status, shift=shift or None, in_time=in_time, out_time=out_time, derive_status=derive
	)


def owned_target(attendance_rows, punches):
	"""The submitted row an edit replaces, or None. Raises for a day the editor
	must not touch: a draft, a leave, a mirrored row or punch, two rows."""
	for row in attendance_rows:
		if cint(row.docstatus) == 0:
			raise RowRefused("draft", _("{0} is a draft; submit or delete it first.").format(row.name))
		if row.synced_from_instance:
			raise RowRefused("mirrored", _("{0} is mirrored; change it on the source ERP.").format(row.name))
		if row.leave_type or row.status == "On Leave" or cint(row.modify_half_day_status):
			raise RowRefused("leave", _("{0} is a leave; change the leave application.").format(row.name))
	if any(p.synced_from_instance for p in punches):
		raise RowRefused("mirrored", _("This day's punches are mirrored; change them on the source ERP."))
	submitted = [row for row in attendance_rows if cint(row.docstatus) == 1]
	if len(submitted) > 1:
		# ceiling: one attendance row per day, upgrade: target a row by shift when
		# split-shift days (two non-overlapping shifts) need editing here
		raise RowRefused("multiple_rows", _("This day has more than one attendance row; edit it in Desk."))
	return submitted[0] if submitted else None


def fallback_shift(snap, emp):
	if snap["assignments"]:
		return snap["assignments"][0].shift_type
	return emp.default_shift or next((p.shift for p in snap["punches"] if p.shift), None)


def carry_to(target, changes, old_day, new_day) -> dict:
	"""A moved row keeps what HR did not change, its times shifted to the new date."""
	carried = dict(changes)
	if not target:
		return carried
	if not ("in_time" in changes or "out_time" in changes):
		carried.setdefault("status", target.status)
	carried.setdefault("shift", target.shift)
	if "in_time" not in changes and "out_time" not in changes and target.in_time:
		delta = new_day - old_day
		carried["in_time"] = get_datetime(target.in_time) + delta
		carried["out_time"] = get_datetime(target.out_time) + delta if target.out_time else None
	return carried


def punch_belongs_to(punch, day, attendance_names) -> bool:
	"""A punch belongs to its shift day, or to the clock day when it has no shift."""
	if punch.attendance and punch.attendance in attendance_names:
		return True
	return getdate(punch.shift_start or punch.time) == day


def plan_punches(punches) -> tuple:
	"""HR's own punches by role, and the original punches to skip-stamp. Pure.

	`own`: {"IN": first HR IN, "OUT": last HR OUT, "extra": other HR punches},
	reusable because they are the editor's own. `superseded`: every other
	punch still counted — device, PWA, import, Pending — never re-timed.
	"""
	hr = [p for p in punches if p.device_id == HR_DEVICE]
	own = {}
	for log_type, rows in (("IN", hr), ("OUT", list(reversed(hr)))):
		found = next((p for p in rows if p.log_type == log_type), None)
		if found:
			own[log_type] = found
	chosen = {id(p) for p in own.values()}
	own["extra"] = [p for p in hr if id(p) not in chosen]
	superseded = [
		p
		for p in punches
		if p.device_id not in (HR_DEVICE, HR_REMOVED_DEVICE) and not cint(p.skip_auto_attendance)
	]
	return own, superseded


def punch_stamp(shift, window) -> dict:
	"""The whole shift stamp a punch carries, as fetch_shift would write it."""
	stamp = {
		"shift": shift,
		"shift_start": window.start_datetime,
		"shift_end": window.end_datetime,
		"shift_actual_start": window.actual_start,
		"shift_actual_end": window.actual_end,
		"offshift": 0,
		"skip_auto_attendance": 0,
	}
	if window.get("overtime_type"):
		stamp["overtime_type"] = window.overtime_type
	return stamp


def engine_day(shift_doc, employee, window, in_time, out_time, half_holiday=False):
	"""HR's in and out through the hourly job's own day rule
	(ShiftType.get_attendance, with shift_day_result's thresholds): pairing,
	unpaid early arrival, unpaid breaks, late entry / early exit and status."""
	from hrms.hr.doctype.shift_type.shift_type import ShiftType

	stamp = {
		"employee": employee,
		"shift": shift_doc.name,
		"shift_start": window.start_datetime,
		"shift_end": window.end_datetime,
		"shift_actual_start": window.actual_start,
		"shift_actual_end": window.actual_end,
		"skip_auto_attendance": 0,
		"offshift": 0,
		"remote_approval_status": None,
		"overtime_type": window.get("overtime_type"),
	}
	logs = [
		frappe._dict(name="hr-in", time=in_time, log_type="IN", **stamp),
		frappe._dict(name="hr-out", time=out_time, log_type="OUT", **stamp),
	]
	absent = flt(shift_doc.working_hours_threshold_for_absent)
	half = flt(shift_doc.working_hours_threshold_for_half_day)
	if half_holiday:
		absent, half = absent / 2, half / 2
	status, hours, late, early, _in, _out = ShiftType.get_attendance(shift_doc, logs, absent, half)
	logger.info(
		"[attendance_master_edit] engine day for %s %s-%s on %s: %s %.2fh",
		employee,
		in_time,
		out_time,
		shift_doc.name,
		status,
		flt(hours),
	)
	return frappe._dict(
		status=status, working_hours=flt(hours, 2), late_entry=bool(late), early_exit=bool(early)
	)


def describe_changes(before, after) -> list:
	before = before or {}
	parts = []
	for field, label in (("status", "status"), ("shift", "shift"), ("in_time", "in"), ("out_time", "out")):
		old, new = before.get(field), after.get(field)
		if _show(old) != _show(new):
			parts.append(f"{label} {html.escape(_show(old))} → {html.escape(_show(new))}")
	return parts


def _show(value) -> str:
	if value in (None, ""):
		return "—"
	if isinstance(value, datetime):
		return value.strftime("%Y-%m-%d %H:%M")
	return str(value)


def revision_of(attendance, punches, assignments) -> str:
	parts = sorted(
		[f"A|{r.name}|{cint(r.docstatus)}|{r.modified}" for r in attendance]
		+ [f"P|{p.name}|{p.modified}" for p in punches]
		+ [f"S|{a.name}|{a.modified}" for a in assignments]
	)
	return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:20]


# --- reads --------------------------------------------------------------------------


def _snapshot(emp, day) -> dict:
	attendance = _day_attendance(emp.name, day)
	punches = _day_punches(emp.name, day, [r.name for r in attendance])
	assignments = _day_assignments(emp.name, day)
	for row in attendance:
		row["hr_owned"] = bool(
			cint(row.docstatus) == 1
			and not cint(row.auto_attendance)
			and not row.synced_from_instance
			and not row.leave_type
		)
	for punch in punches:
		punch["hr_entered"] = punch.device_id in (HR_DEVICE, HR_REMOVED_DEVICE)
	logger.debug(
		"[attendance_master_edit] snapshot %s %s: %d row(s) %d punch(es)",
		emp.name,
		day,
		len(attendance),
		len(punches),
	)
	return {
		"employee": emp.name,
		"employee_name": emp.employee_name,
		"company": emp.company,
		"attendance_date": str(day),
		"default_shift": emp.default_shift,
		"attendance": attendance,
		"punches": punches,
		"assignments": assignments,
		"revision": revision_of(attendance, punches, assignments),
	}


def _require_hr() -> None:
	frappe.only_for(HR_ROLES)


def _is_system_manager() -> bool:
	return frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles()


def _require_employee(employee, lock: bool):
	emp = _employee(employee, lock=lock)
	if not emp:
		raise RowRefused("not_found", _("Employee {0} not found.").format(employee))
	if not company_scope.company_visible(emp.company):
		raise RowRefused("fenced", _("You are not permitted to change {0}'s attendance.").format(employee))
	return emp


# --- seams: every database touch, one small function each -------------------------


def _today():
	return getdate(now_datetime())


def _employee(employee, lock=False):
	# ceiling: the Employee row lock serializes HR edits per person; the hourly
	# job does not take it and is kept out by Attendance's duplicate check,
	# upgrade: a named lock if a second writer ever inserts HR-owned rows
	return frappe.db.get_value(
		"Employee",
		employee,
		["name", "employee_name", "company", "default_shift"],
		as_dict=True,
		for_update=lock,
	)


def _day_attendance(employee, day):
	return frappe.get_all(
		"Attendance",
		filters={"employee": employee, "attendance_date": day, "docstatus": ["<", 2]},
		fields=ATTENDANCE_FIELDS,
		order_by="creation asc",
	)


def _day_punches(employee, day, attendance_names):
	start, end = f"{day} 00:00:00", f"{day} 23:59:59"
	or_filters = [["shift_start", "between", [start, end]], ["time", "between", [start, end]]]
	if attendance_names:
		or_filters.append(["attendance", "in", list(attendance_names)])
	rows = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee},
		or_filters=or_filters,
		fields=PUNCH_FIELDS,
		order_by="time asc",
	)
	return [row for row in rows if punch_belongs_to(row, day, attendance_names)]


def _day_assignments(employee, day):
	return frappe.get_all(
		"Shift Assignment",
		filters={"employee": employee, "docstatus": 1, "status": "Active", "start_date": ["<=", day]},
		or_filters=[["end_date", ">=", day], ["end_date", "is", "not set"]],
		fields=ASSIGNMENT_FIELDS,
		order_by="start_date desc",
	)


def _financial_dependency(employee, day, attendance_name):
	from hrms.overrides.remote_checkin_request_hooks import _repair_financial_dependency

	return _repair_financial_dependency(employee, day, attendance_name, for_update=True)


def _cancel_attendance(name):
	doc = frappe.get_doc("Attendance", name)
	doc.flags.ignore_permissions = True
	doc.cancel()


def _shift_doc(shift):
	return frappe.get_cached_doc("Shift Type", shift)


def _is_half_holiday(shift_doc, employee, day):
	return shift_doc.is_half_holiday(employee, day)


def _shift_window(shift, day):
	from frappe.utils import to_timedelta

	from hrms.hr.doctype.shift_assignment.shift_assignment import get_shift_details

	start_time = frappe.db.get_value("Shift Type", shift, "start_time")
	anchor = datetime.combine(day, time()) + to_timedelta(start_time)
	return get_shift_details(shift, anchor)


def _update_punch(name, fields):
	# validate is skipped as the off-shift heal does: fetch_shift would replace
	# HR's shift and the geofence judges a live punch, not HR's correction.
	# Mirrored punches were refused before this (write_block runs in validate).
	doc = frappe.get_doc("Employee Checkin", name)
	doc.update(fields)
	doc.flags.ignore_validate = True
	doc.flags.ignore_permissions = True
	doc.save()


def _insert_punch(fields):
	doc = frappe.get_doc({"doctype": "Employee Checkin", **fields})
	doc.flags.ignore_validate = True
	doc.flags.ignore_permissions = True
	# HR's typed night IN must not pull the next morning's punches onto its
	# shift (G1-W2): the editor states the whole day itself.
	doc.flags.skip_session_restamp = True
	doc.insert()
	return doc.name


def _set_skip(name, value):
	frappe.db.set_value("Employee Checkin", name, "skip_auto_attendance", value)


def _skip_marked(names):
	return set(
		frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "Employee Checkin",
				"reference_name": ["in", list(names)],
				"content": ["like", f"%{SKIP_MARKER}%"],
			},
			pluck="reference_name",
		)
	)


def _delete_punch(name):
	frappe.delete_doc("Employee Checkin", name, ignore_permissions=True)


def _insert_attendance(fields):
	doc = frappe.new_doc("Attendance")
	doc.update(fields)
	doc.flags.ignore_permissions = True
	doc.insert()
	doc.submit()
	return frappe._dict(
		name=doc.name, status=doc.status, working_hours=doc.working_hours, ot_hours=doc.get("ot_hours")
	)


def _link_punches(names, attendance):
	from hrms.hr.doctype.employee_checkin.employee_checkin import update_attendance_in_checkins

	update_attendance_in_checkins(names, attendance)


def _submit_assignment(fields):
	doc = frappe.get_doc({"doctype": "Shift Assignment", **fields})
	doc.flags.ignore_permissions = True
	doc.insert()
	doc.submit()
	return doc.name


def _comment(doctype, name, text):
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": doctype,
			"reference_name": name,
			"content": text,
		}
	).insert(ignore_permissions=True)


def _enqueue_engine(shift):
	frappe.enqueue(
		"hrms.utils.offshift_punch_heal.process_shift_types",
		queue="long",
		timeout=3600,
		shift_types=[shift],
		enqueue_after_commit=True,
	)
