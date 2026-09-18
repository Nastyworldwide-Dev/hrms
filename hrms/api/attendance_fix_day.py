"""HR Fix Day — HR corrects the EVIDENCE, the engine recomputes the result.

Owner rule (Nabil, 16 Sep 2026): "HR corrects the evidence, never the result."
HR picks taps; hours, break, the OT ladder and claimability are recomputed by
the one engine every other path uses. Nothing here types hours or overtime, and
nothing here writes `working_hours` or `ot_hours` — every earlier defect in this
area came from a second place doing the same maths (pinned by an AST test,
hrms/tests/test_attendance_fix_day_writes_no_hours.py).

One employee, one day. Five actions, nothing free-form:

    pair_taps(a, b)                     two taps become one session
    move_tap(tap, shift=, day=)         re-stamp to another shift or shift day
    ignore_tap(tap, reason)             not counted, reason recorded
    restore_tap(tap, reason)            undo an ignore (including a rejection's)
    add_tap(employee, moment, log_type, reason)   a tap entered by HR

and `undo_fix(log_entry)`, which puts back exactly what one action changed.

What holds the line:

* A COUNTED tap (not skipped, not rejected — the evidence the day is built
  from) keeps its time and its log type for ever. Only its shift stamp and its
  skip tick may change, and `_write_tap` is the only writer, so no action can
  route around that (`counted_tap_change_reason`).
* A day that is paid, carries approved overtime, is a leave or half-day leave,
  came from an Attendance Request, or was removed by HR is refused with a plain
  sentence naming the reason — HR cancels that first (`day_block_reason`).
  A future day and a shift still running are refused the same way.
* Every action leaves a Comment on each tap it touched (who, what, why), an
  HR Day Fix Log entry carrying the day before and after, and an IMMEDIATE
  re-mark through `hrms.utils.day_remark.remark_day` — the same engine the
  hourly job and the recovery use. The before/after goes back to the screen.
* Reads and writes are HR-only (`frappe.only_for`) and company-fenced
  (`company_scope.company_visible`), over POST.

The free-form day — the rare true manual correction — stays where it was: the
Shift Attendance master edit (`hrms.api.attendance_master_edit`). This screen
never types a status, an hour or an OT figure.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate

from hrms.overrides import company_scope
from hrms.utils import hr_removed_day

logger = logging.getLogger(__name__)

HR_ROLES = ("HR User", "HR Manager", "System Manager")
#: device_id of a tap HR typed here, the master edit's marker one screen further on
HR_TAP_DEVICE = "HR fix day"
#: two taps wider apart than this are not one session (owner rule, 16 Sep 2026)
MAX_PAIR_GAP_HOURS = 20
LOG_DOCTYPE = "HR Day Fix Log"
#: this screen's value for the log's `source`. The log is shared: the automatic
#: ERP backfill and the recovery write their own entries with their own source,
#: so a reader can tell a person's correction from a machine's.
LOG_SOURCE = "hr_fix_day"
ACTIONS = (
	"rebuild_day",
	"pair_taps",
	"move_tap",
	"ignore_tap",
	"restore_tap",
	"add_tap",
	"remove_duplicate_row",
	"undo_fix",
)
#: What this screen may change on a tap. `time` and `log_type` are deliberately
#: absent: the shift stamp says which session a tap belongs to, the skip tick
#: says whether it counts, and neither re-writes what the device recorded.
CHANGEABLE_TAP_FIELDS = frozenset(
	(
		"shift",
		"shift_start",
		"shift_end",
		"shift_actual_start",
		"shift_actual_end",
		"offshift",
		"overtime_type",
		"skip_auto_attendance",
		# says WHY it was skipped: noise (read across it) or not-verified (a wall)
		"skipped_as_noise",
		"remote_approval_status",
		# the link to the row the tap was evidence for: re-stamping a tap
		# releases it, so both days can be rebuilt from the taps they now hold
		"attendance",
	)
)
#: ... and of those, what a COUNTED tap still allows.
COUNTED_TAP_FIELDS = frozenset(
	(
		"shift",
		"shift_start",
		"shift_end",
		"shift_actual_start",
		"shift_actual_end",
		"offshift",
		"overtime_type",
		"skip_auto_attendance",
		# ignoring a counted tap says it is noise, in the same write
		"skipped_as_noise",
		"attendance",
	)
)
TAP_FIELDS = [
	"name",
	"employee",
	"time",
	"log_type",
	"shift",
	"shift_start",
	"shift_end",
	"shift_actual_start",
	"shift_actual_end",
	"attendance",
	"skip_auto_attendance",
	"skipped_as_noise",
	"device_id",
	"offshift",
	"overtime_type",
	"synced_from_instance",
	"remote_approval_status",
]
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
	"ot_hours",
	"auto_attendance",
	"leave_type",
	"leave_application",
	"attendance_request",
	"modify_half_day_status",
	"synced_from_instance",
]


class Refused(frappe.ValidationError):
	"""This screen must not do what was asked; the message is the plain reason."""


# --- pure rules ------------------------------------------------------------------


def tap_state(tap) -> str:
	"""What this tap is worth to the day, in HR's words. Pure.

	Order matters: a rejected tap is rejected even when it is also skipped (the
	rejection is what skipped it), and a tap HR typed here is still "skipped"
	once somebody ignores it.
	"""
	if (tap.get("remote_approval_status") or "") == "Rejected":
		return "rejected"
	if cint(tap.get("skip_auto_attendance")):
		return "skipped"
	if (tap.get("remote_approval_status") or "") == "Pending":
		return "awaiting approval"
	if tap.get("device_id") == HR_TAP_DEVICE:
		return "HR-entered"
	return "counted"


def counted(tap) -> bool:
	"""Whether the engine reads this tap as evidence. Pure."""
	return tap_state(tap) in ("counted", "HR-entered")


def counted_tap_change_reason(tap, fields) -> str | None:
	"""Why these fields may not be written to this tap, or None. Pure.

	The rule HR asked for: a counted tap keeps its time — only its shift and
	its skip tick may change. A tap that is already skipped or rejected is not
	evidence, so this screen may still not re-time it either: `time` and
	`log_type` are never changeable, whatever the state.
	"""
	asked = {
		field for field, value in dict(fields).items() if value is not None or field in CHANGEABLE_TAP_FIELDS
	}
	forbidden = sorted(asked - CHANGEABLE_TAP_FIELDS)
	if forbidden:
		return _("A tap keeps what the device recorded; {0} cannot be changed here.").format(
			", ".join(forbidden)
		)
	if not counted(tap):
		return None
	locked = sorted(asked - COUNTED_TAP_FIELDS)
	if locked:
		return _(
			"This tap is counted in the day, so it keeps its time; only its shift or whether it "
			"counts may change ({0} was asked for)."
		).format(", ".join(locked))
	return None


def pair_refusal(first, second, max_gap_hours=MAX_PAIR_GAP_HOURS) -> str | None:
	"""Why these two taps are not one session, or None. Pure."""
	if not first or not second:
		return _("Pick two taps of the same day.")
	if first.get("name") == second.get("name"):
		return _("Pick two different taps; a tap cannot be paired with itself.")
	if first.get("employee") != second.get("employee"):
		return _("These taps belong to two different people.")
	start, end = get_datetime(first.get("time")), get_datetime(second.get("time"))
	if end <= start:
		return _("The second tap must be later than the first.")
	gap = (end - start).total_seconds() / 3600
	if gap > max_gap_hours:
		return _("These taps are {0} hours apart; a session is at most {1} hours.").format(
			round(gap, 1), max_gap_hours
		)
	return None


def day_block_reason(
	day,
	today,
	rows,
	financial=None,
	removed_by_hr=False,
	request=None,
	shift_running=False,
	duplicate_rows_ok=False,
) -> str | None:
	"""Why this employee-day must not be touched here, in one sentence, or None. Pure.

	Deliberately NOT a reason: `auto_attendance = 0`. A day HR marked by hand is
	exactly a day HR may still correct the evidence of; whether the engine then
	re-marks it is the re-mark's own decision (`attendance_recovery`), and the
	answer comes back to the screen.
	"""
	day = getdate(day)
	if day >= getdate(today):
		return _("This day is not over yet; fix it once the day has ended.")
	if shift_running:
		return _("A shift on this day is still running; fix it once the shift has ended.")
	if removed_by_hr:
		return _("HR removed this day in Shift Attendance. Hand the day back there first.")
	for row in rows or []:
		if cint(row.get("docstatus")) == 2:
			continue
		name = row.get("name")
		if row.get("leave_type") or row.get("leave_application") or row.get("status") == "On Leave":
			return _("{0} is a leave day. Cancel the leave first.").format(name)
		if cint(row.get("modify_half_day_status")):
			return _("{0} is a half-day leave. Cancel the leave first.").format(name)
		if row.get("attendance_request"):
			return _("{0} came from an Attendance Request. Cancel that request first.").format(name)
		if row.get("synced_from_instance"):
			# The same line this screen already draws for a mirrored TAP. Without
			# it the row was refused three layers down by the re-mark, which the
			# screen could only report as "nothing changed" (review of b9794c65b).
			return _("{0} is {1}'s copy of this day; it is corrected there.").format(
				name, row["synced_from_instance"]
			)
	if not duplicate_rows_ok:
		live = [row for row in rows or [] if cint(row.get("docstatus")) != 2]
		if len(live) > 1:
			# The engine cannot re-mark a day that already has a row, so every
			# action that rebuilds the day is a no-op here — and it used to be
			# reported as a success. Owner, 17 Sep 2026, on Norazlin's 4 Sep:
			# pairing answered "The day was rebuilt" over Frappe's own
			# "Attendance ... is already marked", with before and after
			# identical. `remove_duplicate_row` waives this for itself; it is
			# the way out, and it is a button on this same screen.
			return _(
				"This day has {0} attendance rows ({1}). Remove the duplicate first — nothing else "
				"can rebuild the day while both exist."
			).format(len(live), ", ".join(sorted(str(row.get("name")) for row in live)))
	if request:
		return _("{0} speaks for this day. Cancel it first.").format(request)
	if financial:
		return _("This day is already paid or carries approved overtime ({0}). Cancel that first.").format(
			financial
		)
	return None


def duplicate_refusal(target, rows) -> str | None:
	"""Why this row may not be cancelled as the day's duplicate, or None. Pure.

	The rule is the one `hrms.sync.erp_backfill.resolve_duplicates` already
	uses, so the machine and the person answer the same question the same way:
	KEEP the row the day's punches are linked to — that is the day that was
	actually worked — and cancel the other.

	Two rows holding the same number of punches is not a coin toss: there is
	nothing to prefer, so it is refused and HR moves a tap first.
	"""
	live = [row for row in rows or [] if cint(row.get("docstatus")) != 2]
	if len(live) < 2:
		return _("This day has only one attendance row; there is no duplicate to remove.")
	if not any(row.get("name") == target.get("name") for row in live):
		return _("{0} is not a live attendance row on this day.").format(target.get("name"))
	if "docstatus" in target and cint(target["docstatus"]) == 0:
		# `doc.cancel()` refuses a draft with a raw framework error, and this
		# screen answers in sentences. A draft is also not what makes a day
		# read wrong — nothing counts it — so Desk is the right place for it.
		return _("{0} is a draft. Submit or delete it in Desk; a draft counts toward nothing.").format(
			target.get("name")
		)

	most = max(cint(row.get("linked_punches")) for row in live)
	mine = cint(target.get("linked_punches"))
	if not most:
		return None  # no punches anywhere: nothing to protect, HR decides
	if mine < most:
		return None
	holders = [row for row in live if cint(row.get("linked_punches")) == most]
	if len(holders) > 1:
		return _("{0} and {1} hold the same punches. Move a tap to the row it belongs to first.").format(
			*sorted(row.get("name") for row in holders)[:2]
		)
	other = next(row.get("name") for row in live if row.get("name") != target.get("name"))
	return _("{0} holds this day's punches. Remove {1} instead.").format(target.get("name"), other)


#: a dropped tap this far from the next one is named on screen, so HR sees the
#: size of the hole the rule leaves before it is written (owner rule, 17 Sep 2026)
GAP_NOTE_HOURS = 2


def _evidence(taps) -> list:
	"""The day's counted taps, earliest first. Pure.

	A mirrored tap belongs to the site that recorded it, and an ignored or
	rejected tap is not evidence — neither is read, and neither is touched.
	"""
	live = [tap for tap in taps or [] if counted(tap) and not tap.get("synced_from_instance")]
	return sorted(live, key=lambda tap: get_datetime(tap.get("time")))


def _gap_words(seconds) -> str:
	hours, rest = divmod(int(seconds), 3600)
	return _("{0} h {1} m").format(hours, rest // 60)


#: How a shift decides which tap opens a session and which closes it. Under the
#: alternating reading the device's own IN/OUT label is not consulted at all —
#: the first counted tap opens the day and the last one closes it.
ALTERNATING_PAIRING = "Alternating entries as IN and OUT during the same shift"


def day_plan(taps, rows, pairing: str | None = None) -> dict:
	"""What this day should look like, read from its own evidence. Pure.

	Owner ruling, 17 Sep 2026, after correcting one day by hand through five
	dialogs: "the 11 am out is possible accidental and should be fine for us to
	fix by removing it alongside the broken glitch stuff. applicable to any
	scenarios."

	So the rule is the simplest one that fits what a shift means: the day's
	FIRST counted IN opens it, its LAST counted OUT closes it, and every counted
	tap between them is noise — the repeated-tap glitch and the accidental
	mid-day OUT alike. An attendance row with no punches behind it is cancelled.

	This supersedes deducting a mid-day gap: the OUT that made the gap is now
	read as a mistap, so somebody who really leaves mid-day and punches out is
	paid for that time unless HR intervenes. The safeguard is not another rule,
	it is SIGHT — `notes` names every long gap this drops, on screen, before a
	single field is written, and the five manual actions are still there for the
	day that looks wrong.

	Where the evidence cannot say this much — nothing opens the day, nothing
	closes it, the OUT precedes the IN, or two rows and no punches anywhere —
	it REFUSES and writes nothing. Guessing a session is how a screen invents
	somebody's pay.
	"""
	empty = {"cancel": [], "session": None, "drop": [], "relabel": [], "notes": [], "refusal": None}
	live = [row for row in rows or [] if cint(row.get("docstatus")) != 2]
	evidence = _evidence(taps)
	if not evidence:
		return {**empty, "refusal": _("This day has no counted taps to read it from.")}

	if pairing == ALTERNATING_PAIRING:
		# The shift does not read the device's label, so neither does this.
		# Owner, 18 Sep 2026, on a day the device recorded as two INs: the engine
		# marked it Present with 8.04 h from exactly those two taps, and the
		# planner refused it — stricter than the engine it plans for, sending HR
		# to hunt a fault that was not there.
		opening = evidence[0]
		closing = evidence[-1] if len(evidence) > 1 else None
		if not closing:
			return {
				**empty,
				"refusal": _("This day has one counted tap; a session needs two. Add the missing one."),
			}
	else:
		opening = next((tap for tap in evidence if (tap.get("log_type") or "") == "IN"), None)
		closing = next((tap for tap in reversed(evidence) if (tap.get("log_type") or "") == "OUT"), None)
		if not opening:
			return {**empty, "refusal": _("Nothing opens this day: it has no counted IN tap.")}
		if not closing:
			return {**empty, "refusal": _("Nothing closes this day: it has no counted OUT tap.")}
	# The same rule the manual pair answers with, asked the same way: a session
	# HR is forbidden to build by hand is not one this may build in one press.
	# Review of d00b4de62: without this, taps at 00:05 and 23:55 became a
	# twenty-four hour "session" and the engine priced it.
	session_refusal = pair_refusal(opening, closing)
	if session_refusal:
		return {**empty, "refusal": session_refusal}

	# An empty row beside a worked one is the ghost the endgame leaves behind.
	# With punches nowhere there is nothing to prefer, which is HR's call and
	# not a screen's — the same answer `erp_backfill.resolve_duplicates` gives.
	cancel = []
	if len(live) > 1:
		worked = [row for row in live if cint(row.get("linked_punches"))]
		if len(worked) > 1:
			# Two rows that BOTH hold punches are two real sessions, not a ghost
			# beside a worked day. Merging them would re-stamp the second
			# shift's closing tap onto the first shift and swallow the gap
			# between them as noise (review of d00b4de62).
			return {
				**empty,
				"refusal": _(
					"This day has two attendance rows and punches on both ({0}). That is two "
					"sessions, not a duplicate — correct it by hand."
				).format(", ".join(sorted(str(row.get("name")) for row in worked))),
			}
		if not worked:
			return {
				**empty,
				"refusal": _(
					"This day has {0} attendance rows and no punches point at any of them. "
					"Remove the one that should go, by hand."
				).format(len(live)),
			}
		cancel = [
			{
				"name": row.get("name"),
				"shift": row.get("shift"),
				"status": row.get("status"),
				"why": _("no punches point at it"),
			}
			for row in live
			if not cint(row.get("linked_punches"))
		]

	# The punch page must read like the result. Owner ruling, 18 Sep 2026, after
	# a day the device recorded as two INs came out right in Attendance and
	# wrong on the check-in list: "check in must show correct in and out despite
	# it was in in or anything". This REVERSES the 16 Sep rule that a tap keeps
	# what the device recorded — for the two taps that ARE the session, and for
	# nothing else. It is shown here before it is applied, recorded on the punch,
	# and put back by the undo.
	relabel = [
		{
			"name": tap.get("name"),
			"time": str(tap.get("time")),
			"from": tap.get("log_type"),
			"to": wanted,
		}
		for tap, wanted in ((opening, "IN"), (closing, "OUT"))
		if (tap.get("log_type") or "") != wanted
	]

	keep = {opening.get("name"), closing.get("name")}
	drop, notes = [], []
	for index, tap in enumerate(evidence):
		if tap.get("name") in keep:
			continue
		drop.append(
			{
				"name": tap.get("name"),
				"time": str(tap.get("time")),
				"log_type": tap.get("log_type"),
				"why": _("between the day's first in and last out"),
			}
		)
		following = evidence[index + 1] if index + 1 < len(evidence) else None
		if not following:
			continue
		gap = (get_datetime(following.get("time")) - get_datetime(tap.get("time"))).total_seconds()
		if gap >= GAP_NOTE_HOURS * 3600:
			notes.append(
				_("{0} {1} sat {2} before the next tap.").format(
					fd_clock_text(tap.get("time")), tap.get("log_type"), _gap_words(gap)
				)
			)
	logger.info(
		"[attendance_fix_day] plan: keep %s -> %s, drop %d tap(s), cancel %s",
		opening.get("name"),
		closing.get("name"),
		len(drop),
		[entry["name"] for entry in cancel],
	)
	return {
		"cancel": cancel,
		"session": {"in": tap_view(opening), "out": tap_view(closing)},
		"drop": drop,
		"relabel": relabel,
		"notes": notes,
		"refusal": None,
	}


def fd_clock_text(value) -> str:
	"""The clock part of a stamp, for a sentence HR reads. Pure."""
	text = str(value or "")
	return text[11:19] or text


def tap_view(tap) -> dict:
	"""One tap as the screen shows it. Pure."""
	return {
		"name": tap.get("name"),
		"time": str(tap.get("time")) if tap.get("time") else None,
		"log_type": tap.get("log_type"),
		"shift": tap.get("shift"),
		"shift_start": str(tap.get("shift_start")) if tap.get("shift_start") else None,
		"state": tap_state(tap),
		"counted": counted(tap),
		"device_id": tap.get("device_id"),
		"attendance": tap.get("attendance"),
		"mirrored": bool(tap.get("synced_from_instance")),
	}


def row_view(row) -> dict:
	"""One Attendance row as the screen shows it — read only, never written back."""
	return {
		"name": row.get("name"),
		"date": str(getdate(row.get("attendance_date"))) if row.get("attendance_date") else None,
		"docstatus": cint(row.get("docstatus")),
		"status": row.get("status"),
		"shift": row.get("shift"),
		"in_time": str(row.get("in_time")) if row.get("in_time") else None,
		"out_time": str(row.get("out_time")) if row.get("out_time") else None,
		"hours": round(flt(row.get("working_hours")), 2),
		"overtime": round(flt(row.get("ot_hours")), 2),
		"marked_by_hr": not cint(row.get("auto_attendance")),
	}


def tap_snapshot(tap) -> dict:
	"""Everything the undo needs to put this tap back exactly as it was. Pure."""
	return {
		field: (str(tap.get(field)) if isinstance(tap.get(field), datetime) else tap.get(field))
		for field in TAP_FIELDS
	}


# --- endpoints --------------------------------------------------------------------


@frappe.whitelist(methods=["POST"])
def get_day(employee: str, date: str) -> dict:
	"""The screen: every tap of the day, the Attendance row(s), who owns the day,
	and — when the day may not be touched — the sentence saying why."""
	_require_hr()
	emp = _require_employee(employee)
	return _screen(emp, getdate(date))


@frappe.whitelist(methods=["POST"])
def pair_taps(a: str, b: str, reason: str | None = None) -> dict:
	"""Two taps become one session: the second joins the first tap's shift stamp,
	both stop being skipped, and the day is rebuilt."""
	_require_hr()
	first, second = _tap(a), _tap(b)
	refusal = pair_refusal(first, second)
	if refusal:
		_refuse(refusal)
	emp = _require_employee(first.employee)
	days = _days_of(first, second)
	_lock_and_guard(emp.name, days)
	stamp = _session_stamp(first)
	before = _before(emp.name, days, [first, second])
	_write_tap(first, {"skip_auto_attendance": 0})
	# `attendance: None` releases the tap from the row it was evidence for.
	# Without it the engine still reads the tap as another day's, so NEITHER
	# day rebuilds: the old day keeps a row no evidence supports and the new
	# day never sees the tap (found on fresh.local, fix_day_probe).
	_write_tap(second, {**stamp, "skip_auto_attendance": 0, "attendance": None})
	note = _("paired with {0} as one session on {1}").format(first.name, stamp.get("shift"))
	return _finish(emp, days, "pair_taps", reason, {second.name: note, first.name: note}, before)


@frappe.whitelist(methods=["POST"])
def move_tap(tap: str, shift: str | None = None, day: str | None = None, reason: str | None = None) -> dict:
	"""Re-stamp a tap to another shift or another shift day. Both days are rebuilt."""
	_require_hr()
	row = _tap(tap)
	if not shift and not day:
		_refuse(_("Say which shift or which day this tap belongs to."))
	emp = _require_employee(row.employee)
	target_day = getdate(day) if day else _tap_day(row)
	target_shift = shift or row.shift
	if not target_shift:
		_refuse(_("This tap has no shift. Choose the shift it belongs to."))
	days = sorted({_tap_day(row), target_day})
	# The second action allowed on a two-row day, and for the same reason: it is
	# a way OUT of one. When two rows hold the same punch count there is nothing
	# to prefer between them, so `duplicate_refusal` sends HR here to move a tap
	# and break the tie — a sentence that was only true while this door was open
	# (review of f45a0f593). Moving the tap is the whole value; the day itself
	# will not rebuild until one row is gone, and the screen now says so plainly
	# instead of reporting a rebuild that did not happen.
	_lock_and_guard(emp.name, days, duplicate_rows_ok=True)
	before = _before(emp.name, days, [row])
	# released from its old row for the same reason pairing releases one
	_write_tap(row, {**_shift_stamp(target_shift, target_day), "attendance": None})
	note = _("moved to {0} on {1}").format(target_shift, target_day)
	return _finish(emp, days, "move_tap", reason, {row.name: note}, before)


@frappe.whitelist(methods=["POST"])
def ignore_tap(tap: str, reason: str) -> dict:
	"""Mark a tap not counted, with the reason recorded on it, and rebuild."""
	_require_hr()
	reason = _require_reason(reason)
	row = _tap(tap)
	emp = _require_employee(row.employee)
	days = [_tap_day(row)]
	# The day guard first: "cancel the payroll first" is what HR needs to hear,
	# even when the tap itself would also have been refused.
	_lock_and_guard(emp.name, days)
	if cint(row.skip_auto_attendance):
		_refuse(_("This tap is already ignored."))
	before = _before(emp.name, days, [row])
	# NOISE, not "unverified": HR looked at this tap and said it is not there, so
	# the day reads straight across it. Everything else that is skipped stays a
	# wall (hrms.hr.doctype.shift_type.shift_type.splits_the_day).
	_write_tap(row, {"skip_auto_attendance": 1, "skipped_as_noise": 1})
	return _finish(emp, days, "ignore_tap", reason, {row.name: _("ignored: not counted in the day")}, before)


@frappe.whitelist(methods=["POST"])
def restore_tap(tap: str, reason: str) -> dict:
	"""Bring an ignored tap back — including one a rejected request left behind —
	and rebuild.

	A tap the approver REJECTED is not read by the engine even with the skip
	tick cleared, so restoring one also clears the rejection. That is a decision
	being overturned, so it is named in the comment, kept in the log, and the
	undo puts the rejection back.
	"""
	_require_hr()
	reason = _require_reason(reason)
	row = _tap(tap)
	emp = _require_employee(row.employee)
	days = [_tap_day(row)]
	_lock_and_guard(emp.name, days)
	rejected = (row.get("remote_approval_status") or "") == "Rejected"
	if not cint(row.skip_auto_attendance) and not rejected:
		_refuse(_("This tap already counts in the day."))
	before = _before(emp.name, days, [row])
	# `_write_tap` clears the noise verdict with the skip; both are named here
	# because this is the action whose whole point is that the tap counts again.
	fields = {"skip_auto_attendance": 0, "skipped_as_noise": 0}
	if rejected:
		fields["remote_approval_status"] = "Approved"
	_write_tap(row, fields)
	note = (
		_("restored, and the rejection on it cleared, so the day counts it again")
		if rejected
		else _("restored: counted in the day again")
	)
	return _finish(emp, days, "restore_tap", reason, {row.name: note}, before)


@frappe.whitelist(methods=["POST"])
def add_tap(employee: str, moment: str, log_type: str, reason: str) -> dict:
	"""Insert a missing tap, marked as entered by HR, and rebuild its day."""
	_require_hr()
	reason = _require_reason(reason)
	log_type = (log_type or "").strip().upper()
	if log_type not in ("IN", "OUT"):
		_refuse(_("A tap is an IN or an OUT."))
	when = get_datetime(moment)
	emp = _require_employee(employee)
	day = getdate(when)
	days = [day]
	_lock_and_guard(emp.name, days)
	shift = _resolve_shift(emp, day)
	if not shift:
		_refuse(
			_(
				"This day has no shift, so a tap cannot be placed on it. Give the day a shift in "
				"Shift Attendance first."
			)
		)
	before = _before(emp.name, days, [])
	name = _insert_tap(
		{
			"employee": emp.name,
			"time": when,
			"log_type": log_type,
			"device_id": HR_TAP_DEVICE,
			**_shift_stamp(shift, day),
		}
	)
	logger.info("[attendance_fix_day] %s added %s for %s on %s", frappe.session.user, name, emp.name, day)
	note = _("entered by HR as a {0} at {1}").format(log_type, when)
	return _finish(emp, days, "add_tap", reason, {name: note}, before, added=name)


@frappe.whitelist(methods=["POST"])
def remove_duplicate_row(attendance: str, reason: str) -> dict:
	"""Cancel the attendance row a day should not have, and rebuild that day.

	Reported 17 Sep 2026: a day carrying two rows could not be acted on
	anywhere — the report shows one, the Attendance list shows two, and the
	master edit refuses the day outright. This is the sixth action on the
	evidence, and like the other five it types no hours: the day is re-marked
	from its punches the moment the row is gone.

	CANCELLED, never deleted. The row keeps its name, its links and its
	history, and it stays readable in Desk. A cancelled row cannot be brought
	back by `undo_fix` — Frappe has no un-cancel — so the undo says that in a
	sentence instead of pretending; the day itself is rebuilt from its punches
	either way, which is the real recovery.
	"""
	_require_hr()
	reason = _require_reason(reason)
	row = _attendance(attendance)
	emp = _require_employee(row.employee)
	day = getdate(row.attendance_date)
	# The only action allowed to run on a two-row day: it is what ends one.
	_lock_and_guard(emp.name, [day], duplicate_rows_ok=True)

	rows = _rows_with_punch_counts(emp.name, day)
	# The employee row is locked above, so the day cannot change under us; a
	# target that is not in the list is a stale screen, not a race, and it is
	# refused rather than guessed at with a row carrying no punch count.
	target = next((r for r in rows if r.get("name") == row.name), None)
	refusal = (
		duplicate_refusal(target, rows)
		if target
		else _("{0} is no longer on this day. Reload and look again.").format(row.name)
	)
	if refusal:
		_refuse(refusal)

	before = _before(emp.name, [day], [])
	logger.warning(
		"[attendance_fix_day] cancelling %s (%s, %s punch(es)) on %s for %s by %s",
		row.name,
		row.get("shift"),
		cint((target or {}).get("linked_punches")),
		day,
		emp.name,
		frappe.session.user,
	)
	_cancel_attendance(row.name)
	note = _("cancelled as this day's duplicate attendance row")
	_comment("Attendance", row.name, _("{0} by {1}. Reason: {2}").format(note, frappe.session.user, reason))
	return _finish(emp, [day], "remove_duplicate_row", reason, {}, before)


@frappe.whitelist(methods=["POST"])
def plan_day(employee: str, date: str) -> dict:
	"""What `rebuild_day` would do, in words, writing nothing. HR reads it first."""
	_require_hr()
	emp = _require_employee(employee)
	day = getdate(date)
	rows = _rows_with_punch_counts(emp.name, day)
	taps = _day_taps(emp.name, day)
	plan = day_plan(taps, rows, pairing=_day_pairing(taps))
	plan["blocked"] = _day_block(emp.name, day, rows, for_update=False, duplicate_rows_ok=True)
	return plan


@frappe.whitelist(methods=["POST"])
def rebuild_day(employee: str, date: str, reason: str) -> dict:
	"""Apply the whole plan in one press: the owner asked for one step, not five.

	Nothing here decides anything `day_plan` has not already put on the screen,
	and nothing here types a result — the engine re-marks the day from the
	evidence this leaves behind, exactly as it does for the five single actions.
	"""
	_require_hr()
	reason = _require_reason(reason)
	emp = _require_employee(employee)
	day = getdate(date)
	# It ENDS a two-row day, like remove_duplicate_row: cancelling the empty row
	# is the first thing it does.
	_lock_and_guard(emp.name, [day], duplicate_rows_ok=True)

	taps = _day_taps(emp.name, day)
	plan = day_plan(taps, _rows_with_punch_counts(emp.name, day), pairing=_day_pairing(taps))
	if plan["refusal"]:
		_refuse(plan["refusal"])

	by_name = {tap.get("name"): tap for tap in taps}
	before = _before(emp.name, [day], list(by_name.values()))
	logger.warning(
		"[attendance_fix_day] rebuilding %s on %s for %s: cancel %s, drop %s",
		emp.name,
		day,
		frappe.session.user,
		[entry["name"] for entry in plan["cancel"]],
		[entry["name"] for entry in plan["drop"]],
	)

	for entry in plan["cancel"]:
		_cancel_attendance(entry["name"])
		_comment(
			"Attendance",
			entry["name"],
			_("cancelled by the day rebuild ({0}) by {1}. Reason: {2}").format(
				entry["why"], frappe.session.user, reason
			),
		)

	notes = {}
	for entry in plan["drop"]:
		tap = by_name[entry["name"]]
		if not cint(tap.get("skip_auto_attendance")) or not cint(tap.get("skipped_as_noise")):
			_write_tap(tap, {"skip_auto_attendance": 1, "skipped_as_noise": 1})
		notes[entry["name"]] = _("ignored by the day rebuild: {0}").format(entry["why"])

	opening = by_name[plan["session"]["in"]["name"]]
	closing = by_name[plan["session"]["out"]["name"]]
	stamp = _session_stamp(opening)
	# The label the day is read by, written onto the punch itself, so the
	# check-in page reads like Attendance and the report (owner, 18 Sep 2026).
	wanted = {entry["name"]: entry["to"] for entry in plan["relabel"]}
	open_label = {"log_type": wanted[opening.name]} if opening.name in wanted else {}
	close_label = {"log_type": wanted[closing.name]} if closing.name in wanted else {}
	_write_tap(opening, {"skip_auto_attendance": 0, **open_label}, relabelling=bool(open_label))
	# `attendance: None` for the same reason pairing releases the second tap.
	_write_tap(
		closing,
		{**stamp, "skip_auto_attendance": 0, "attendance": None, **close_label},
		relabelling=bool(close_label),
	)
	session_note = _("kept by the day rebuild as this day's session with {0}").format(opening.get("name"))
	notes[opening.get("name")] = session_note
	notes[closing.get("name")] = session_note
	for entry in plan["relabel"]:
		notes[entry["name"]] = _(
			"relabelled {0} -> {1} by the day rebuild: it is the tap that {2} this day. "
			"The device recorded {0}; the undo puts that back."
		).format(
			entry["from"] or _("nothing"),
			entry["to"],
			_("opens") if entry["to"] == "IN" else _("closes"),
		)

	return _finish(emp, [day], "rebuild_day", reason, notes, before, plan=plan)


@frappe.whitelist(methods=["POST"])
def undo_fix(log_entry: str, reason: str | None = None) -> dict:
	"""Put back exactly what one action changed — tap flags, shift stamp, time —
	then rebuild the same days."""
	_require_hr()
	entry = _log_entry(log_entry)
	if cint(entry.undone):
		_refuse(_("This fix was already undone."))
	cancelled_a_row = entry.action in CANCELLING_ACTIONS and _cancelled_a_row(entry)
	if cancelled_a_row and entry.action not in UNDOABLE_APART_FROM_THE_CANCEL:
		# Frappe has no un-cancel. Saying so is better than a no-op that looks
		# like it worked; the day was rebuilt from its punches when the row
		# went, and correcting the taps is how it is changed from here.
		#
		# `rebuild_day` is here too since the review of d00b4de62: it can cancel
		# rows as well, and undoing one silently would hand HR a brand new row
		# in place of the original, with the original's history orphaned on a
		# permanently cancelled document.
		_refuse(
			_(
				"A cancelled attendance row cannot be brought back. The day was rebuilt from "
				"its punches; correct the taps instead."
			)
		)
	emp = _require_employee(entry.employee)
	before_state = json.loads(entry.before_state or "{}")
	days = sorted(getdate(d) for d in (before_state.get("days") or {}))
	days = days or [getdate(entry.fix_date)]
	_lock_and_guard(emp.name, days)
	before = _before(emp.name, days, [])
	notes = {}
	if entry.action == "add_tap":
		for name in _tap_names(entry):
			_delete_tap(name)
			logger.info("[attendance_fix_day] undo %s deleted the tap HR added: %s", entry.name, name)
	for snapshot in before_state.get("taps") or []:
		_restore_tap_state(snapshot)
		notes[snapshot["name"]] = _("restored to how it stood before {0}").format(entry.name)
	answer = _finish(
		emp,
		days,
		"undo_fix",
		reason or _("undo of {0}").format(entry.name),
		notes,
		before,
		undo_of=entry.name,
	)
	_mark_undone(entry.name)
	if cancelled_a_row:
		# Said out loud rather than left for HR to notice: the taps are back as
		# they were, and the row this pass cancelled stays cancelled, because
		# Frappe has no un-cancel. The day was rebuilt from the taps either way.
		answer["note"] = _(
			"The taps are back as they were. The attendance row this rebuild cancelled "
			"stays cancelled — the day is marked again from its punches."
		)
		logger.info("[attendance_fix_day] undo of %s restored the taps; its cancel stands", entry.name)
	return answer


# --- the shape of one action ------------------------------------------------------


def _day_pairing(taps) -> str | None:
	"""How the shift these taps belong to pairs them, or None when unknown.

	Read from the day's own shift rather than a setting: two employees on two
	shifts can read their days differently, and the planner must answer the way
	the engine will for THAT day.
	"""
	shift = next((tap.get("shift") for tap in taps or [] if tap.get("shift")), None)
	if not shift:
		return None
	pairing = frappe.db.get_value("Shift Type", shift, "determine_check_in_and_check_out")
	logger.debug("[attendance_fix_day] %s pairs taps as: %s", shift, pairing)
	return pairing


def _screen(emp, day) -> dict:
	rows = _day_attendance(emp.name, day)
	taps = _day_taps(emp.name, day)
	return {
		"employee": emp.name,
		"employee_name": emp.employee_name,
		"date": str(day),
		"taps": [tap_view(tap) for tap in taps],
		"attendance": [row_view(row) for row in rows],
		"owner": owner_label(emp.name, day, rows),
		# `blocked` hides every control, so the two-row rule is NOT part of it:
		# the way out of a two-row day is a button on this screen. It comes back
		# as a notice instead — shown above the actions, blocking none of them.
		"blocked": _day_block(emp.name, day, rows, for_update=False, duplicate_rows_ok=True),
		"notice": _day_block(emp.name, day, rows, for_update=False),
	}


def _before(employee, days, taps) -> dict:
	return {
		"days": _day_states(employee, days),
		"taps": [tap_snapshot(tap) for tap in taps],
	}


def _finish(emp, days, action, reason, notes, before, undo_of=None, added=None, plan=None) -> dict:
	"""A Comment on each tap, then the engine's re-mark, then the log entry
	carrying the day before and after. The screen gets both."""
	for name, note in notes.items():
		_comment(
			"Employee Checkin",
			name,
			_("{0} by {1}. Reason: {2}").format(note, frappe.session.user, reason or _("not given")),
		)
	rebuild = {str(day): _rebuild(emp.name, day, f"fix day: {action}") for day in days}
	after = {"days": _day_states(emp.name, days)}
	if added:
		after["added"] = added
	if plan:
		# On the LOG, not just in the answer: the undo reads it to find out
		# whether this pass cancelled a row it cannot bring back.
		after["plan"] = plan
	entry = _write_log(
		{
			"employee": emp.name,
			"fix_date": str(days[0]),
			"action": action,
			"source": LOG_SOURCE,
			"refs": ", ".join(sorted(notes)),
			"reason": reason,
			"fixed_by": frappe.session.user,
			"before_state": json.dumps(before, default=str, indent=1),
			"after_state": json.dumps(after, default=str, indent=1),
			"rebuild": json.dumps(rebuild, default=str, indent=1),
			"undo_of": undo_of,
		}
	)
	logger.info(
		"[attendance_fix_day] %s on %s by %s: %s -> %s (log %s)",
		action,
		", ".join(str(day) for day in days),
		frappe.session.user,
		before.get("days"),
		after.get("days"),
		entry,
	)
	return {"ok": True, "log": entry, "before": before, "after": after, "rebuild": rebuild}


def _day_states(employee, days) -> dict:
	return {str(day): [row_view(row) for row in _day_attendance(employee, day)] for day in days}


def _lock_and_guard(employee, days, duplicate_rows_ok=False) -> None:
	"""The per-employee lock every other writer takes, then the day guards."""
	_lock_employee(employee)
	for day in days:
		blocked = _day_block(
			employee,
			day,
			_day_attendance(employee, day),
			for_update=True,
			duplicate_rows_ok=duplicate_rows_ok,
		)
		if blocked:
			logger.info("[attendance_fix_day] %s on %s refused: %s", employee, day, blocked)
			_refuse(blocked)


def _day_block(employee, day, rows, for_update, duplicate_rows_ok=False) -> str | None:
	return day_block_reason(
		day,
		_today(employee),
		rows,
		financial=_financial(employee, day, rows, for_update),
		removed_by_hr=hr_removed_day.removed_by_hr(employee, day),
		request=_request_cover(employee, day),
		shift_running=_shift_running(employee, day),
		duplicate_rows_ok=duplicate_rows_ok,
	)


def _days_of(*taps) -> list:
	return sorted({_tap_day(tap) for tap in taps})


def _tap_day(tap):
	return getdate(tap.get("shift_start") or tap.get("time"))


def _session_stamp(tap) -> dict:
	"""The first tap's whole shift stamp, so the second joins the same session."""
	if not tap.get("shift") or not tap.get("shift_start"):
		_refuse(
			_("The first tap has no shift, so there is no session to join it to. Move it to a shift first.")
		)
	return {
		"shift": tap.get("shift"),
		"shift_start": tap.get("shift_start"),
		"shift_end": tap.get("shift_end"),
		"shift_actual_start": tap.get("shift_actual_start"),
		"shift_actual_end": tap.get("shift_actual_end"),
	}


def _require_reason(reason) -> str:
	reason = (reason or "").strip()
	if not reason:
		_refuse(_("Say why, so the next person reading this day knows."))
	return reason


def _refuse(sentence) -> None:
	frappe.throw(sentence, Refused)


def owner_label(employee, day, rows) -> str | None:
	"""What Part A's classifier calls this day, as ONE line of text, or None.

	`hrms.utils.attendance_ownership` is another worker's module; this screen
	shows its label when it is there and says nothing when it is not, rather
	than guessing an owner from a blank tick (the defect the endgame plan
	opens with).

	It answers with a verdict PER ROW — a list of dicts — and the header is a
	pill, so the list is folded into one line here. It used to be handed over
	whole and the header printed "[object Object],[object Object]" (owner,
	17 Sep 2026, on Norazlin's 4 September). The day's rows were also being
	passed as the third positional argument, which is `system_users`: the
	accounts that are not people. They are not that, so they are not passed.
	"""
	try:
		from hrms.utils.attendance_ownership import classify_day
	except ImportError:
		logger.debug("[attendance_fix_day] no ownership classifier yet; the screen shows no owner label")
		return None
	try:
		verdicts = classify_day(employee, day)
	except Exception:
		logger.warning("[attendance_fix_day] the ownership classifier failed for %s on %s", employee, day)
		return None
	if isinstance(verdicts, str):
		return verdicts or None
	owners = [str(v.get("owner")) for v in (verdicts or []) if isinstance(v, dict) and v.get("owner")]
	if not owners:
		return None
	# One row: its owner. Several: each one, in the order the rows come back,
	# so a two-row day reads "system, HR" and HR can see which is which.
	return ", ".join(owners)


# --- seams: every database touch, one small function each -------------------------


def _require_hr() -> None:
	frappe.only_for(HR_ROLES)


def _require_employee(employee):
	emp = frappe.db.get_value(
		"Employee", employee, ["name", "employee_name", "company", "default_shift"], as_dict=True
	)
	if not emp:
		_refuse(_("Employee {0} was not found.").format(employee))
	if not company_scope.company_visible(emp.company):
		_refuse(_("You are not permitted to change {0}'s attendance.").format(employee))
	return emp


def _today(employee):
	from hrms.utils.timezone import employee_now

	return employee_now(employee).date()


def _lock_employee(employee) -> None:
	from hrms.hr.doctype.shift_type.shift_type import lock_employee_row

	lock_employee_row(employee)


def _tap(name):
	row = frappe.db.get_value("Employee Checkin", name, TAP_FIELDS, as_dict=True)
	if not row:
		_refuse(_("Tap {0} was not found.").format(name))
	if row.get("synced_from_instance"):
		_refuse(_("This tap came from another site; change it there."))
	return row


def _day_taps(employee, day) -> list:
	"""Every tap of the shift day, plus any tap of the clock day not yet stamped."""
	start = datetime.combine(getdate(day), time.min)
	end = start + timedelta(days=1)
	rows = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee},
		or_filters=[
			["shift_start", ">=", start],
			["time", ">=", start],
		],
		fields=TAP_FIELDS,
		order_by="time asc",
		limit_page_length=0,
	)
	return [row for row in rows if start <= get_datetime(row.get("shift_start") or row.get("time")) < end]


def _day_attendance(employee, day) -> list:
	return frappe.get_all(
		"Attendance",
		filters={"employee": employee, "attendance_date": getdate(day), "docstatus": ["<", 2]},
		fields=ATTENDANCE_FIELDS,
		order_by="creation asc",
	)


def _attendance(name):
	row = frappe.db.get_value("Attendance", name, ATTENDANCE_FIELDS, as_dict=True)
	if not row:
		_refuse(_("Attendance {0} not found.").format(name))
	return row


def _rows_with_punch_counts(employee, day) -> list:
	"""The day's live rows, each carrying how many punches point at it."""
	rows = [dict(row) for row in _day_attendance(employee, day)]
	for row in rows:
		row["linked_punches"] = frappe.db.count("Employee Checkin", {"attendance": row["name"]})
	return rows


def _cancel_attendance(name) -> None:
	doc = frappe.get_doc("Attendance", name)
	doc.flags.ignore_permissions = True
	doc.cancel()


def _financial(employee, day, rows, for_update):
	from hrms.overrides.remote_checkin_request_hooks import _repair_financial_dependency

	submitted = next((r.get("name") for r in rows or [] if cint(r.get("docstatus")) == 1), None)
	return _repair_financial_dependency(employee, getdate(day), submitted, for_update=for_update)


def _request_cover(employee, day):
	from hrms.utils.leave_cover import request_covered_days

	return request_covered_days(employee, day, day).get(getdate(day))


def _shift_running(employee, day) -> bool:
	from hrms.utils.day_remark import _shift_still_running

	return _shift_still_running(employee, getdate(day))


def _shift_stamp(shift, day) -> dict:
	"""The shift stamp a tap carries on that day, as `fetch_shift` would write it —
	through the master edit's own helpers, so there is one such calculation."""
	from hrms.api.attendance_master_edit import _shift_window, punch_stamp

	stamp = punch_stamp(shift, _shift_window(shift, getdate(day)))
	# Moving a tap to another shift says nothing about whether it counts, so the
	# stamp carries neither half of that answer. Dropping only the skip would
	# quietly turn an IGNORED tap from noise into a wall the next time the day
	# was read (the two travel together — see `_write_tap`).
	stamp.pop("skip_auto_attendance", None)
	stamp.pop("skipped_as_noise", None)
	return stamp


def _resolve_shift(emp, day):
	"""The shift a tap entered by HR joins: what the day's other taps already say,
	otherwise the person's default shift."""
	for tap in _day_taps(emp.name, day):
		if tap.get("shift"):
			return tap.get("shift")
	return emp.get("default_shift")


def _write_tap(tap, fields, relabelling: bool = False) -> None:
	"""The ONLY writer of an existing tap: the counted-tap rule lives here, so no
	action can route around it.

	`relabelling` is the one exception, and it is the owner's (18 Sep 2026): the
	day rebuild may write `log_type` on the two taps that ARE the session, so the
	check-in page reads like the result. Nothing else may — not the time, not a
	tap nobody counts, and not any other action — and the plan shows the change
	before it is applied.
	"""
	checked = {field: value for field, value in fields.items() if not (relabelling and field == "log_type")}
	refusal = counted_tap_change_reason(tap, checked)
	if refusal:
		logger.info("[attendance_fix_day] %s refused: %s", tap.get("name"), refusal)
		_refuse(refusal)
	fields = dict(fields)
	if "skip_auto_attendance" in fields and not cint(fields["skip_auto_attendance"]):
		# A tap that counts again carries no verdict. Here rather than at the
		# call sites because there are five of them and `restore_tap` was the
		# only one that remembered — `pair_taps` and the rebuild's session keep
		# both un-skipped a tap and left `skipped_as_noise` set (review of
		# c4a0fca32). A stale tick would make the NEXT skip of that punch read as
		# noise on a judgement nobody gave, which is the whole thing this field
		# exists to prevent.
		fields["skipped_as_noise"] = 0
	frappe.db.set_value("Employee Checkin", tap["name"], fields)
	logger.info(
		"[attendance_fix_day] %s changed by %s: %s", tap.get("name"), frappe.session.user, sorted(fields)
	)


def _restore_tap_state(snapshot) -> None:
	"""The undo's writer: it puts a tap back to a state it really held, so it is
	not bound by the counted-tap rule — that rule stops NEW evidence being
	invented, not an action being reversed."""
	fields = {field: snapshot.get(field) for field in TAP_FIELDS if field not in ("name", "employee")}
	# A snapshot taken before `skipped_as_noise` existed has no such key, and a
	# Check column is not a place to put NULL. 0 is also the right answer: the
	# WALL, which is how that tap read when the snapshot was taken.
	if fields.get("skipped_as_noise") is None:
		fields["skipped_as_noise"] = 0
	frappe.db.set_value("Employee Checkin", snapshot["name"], fields)
	logger.info("[attendance_fix_day] %s restored to its state before the fix", snapshot["name"])


def _insert_tap(fields) -> str:
	doc = frappe.get_doc({"doctype": "Employee Checkin", **fields})
	# As the master edit inserts HR's own punches: `fetch_shift` would replace the
	# shift this screen just resolved, and the geofence judges a live tap, not a
	# correction. The session re-stamp is skipped for the same reason.
	doc.flags.ignore_validate = True
	doc.flags.ignore_permissions = True
	doc.flags.skip_session_restamp = True
	doc.insert()
	return doc.name


def _delete_tap(name) -> None:
	frappe.delete_doc("Employee Checkin", name, ignore_permissions=True)


def _comment(reference_doctype, name, text) -> None:
	"""Leave a note on a record. The DOCTYPE is always said out loud.

	Live, 17 Sep 2026: this was written for taps and named "Employee Checkin"
	itself, then `remove_duplicate_row` passed it an Attendance name. Frappe
	looked for a punch called HR-ATT-2026-15978, did not find one, and threw
	"Could not find Reference Name" — which rolled the request back, the cancel
	with it, so the one action that unblocks a two-row day never completed.
	"""
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": reference_doctype,
			"reference_name": name,
			"content": text,
		}
	).insert(ignore_permissions=True)


def _rebuild(employee, day, reason) -> dict:
	"""The one engine re-mark every other path uses. Never a second calculation here."""
	from hrms.utils.day_remark import remark_day

	# HR is the one asking, on one day, with a reason that is already in the fix
	# log: the "a person keyed this row" hold does not apply to the person it
	# protects. Without this the screen corrected every tap on Norazlin's
	# 4 September and the day stayed Absent (owner, 17 Sep 2026).
	answer = remark_day(employee, day, reason, hr_asked=True)
	logger.info("[attendance_fix_day] re-mark of %s on %s: %s", employee, day, answer)
	return answer


def _write_log(fields) -> str:
	doc = frappe.get_doc({"doctype": LOG_DOCTYPE, **fields})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def _log_entry(name):
	row = frappe.db.get_value(
		LOG_DOCTYPE,
		name,
		["name", "employee", "fix_date", "action", "refs", "before_state", "undone"],
		as_dict=True,
	)
	if not row:
		_refuse(_("Fix {0} was not found.").format(name))
	return row


#: actions that can cancel an attendance row, which Frappe cannot un-cancel
CANCELLING_ACTIONS = ("remove_duplicate_row", "rebuild_day")
#: ... and of those, the ones that did OTHER things worth putting back. A
#: `remove_duplicate_row` IS its cancel, so there is nothing else to restore and
#: refusing is the honest answer. A rebuild also ignored taps, paired a session
#: and relabelled it — refusing all of that because one row cannot come back
#: threw away three recoverable things to be strict about a fourth (review of
#: e1f4165b7, which had promised the relabel was reversible).
UNDOABLE_APART_FROM_THE_CANCEL = ("rebuild_day",)


def _cancelled_a_row(entry) -> bool:
	"""Whether this log entry actually cancelled a row. Pure enough to read.

	`remove_duplicate_row` always does. `rebuild_day` only does when the day
	carried a ghost row, so its own plan is the record: an undo of a rebuild
	that cancelled nothing is an ordinary undo and stays allowed.
	"""
	if entry.action == "remove_duplicate_row":
		return True
	try:
		after = json.loads(entry.after_state or "{}")
	except ValueError:
		logger.warning(
			"[attendance_fix_day] %s has unreadable after_state; assuming it cancelled", entry.name
		)
		return True
	return bool((after.get("plan") or {}).get("cancel"))


def _tap_names(entry) -> list:
	return [name.strip() for name in (entry.get("refs") or "").split(",") if name.strip()]


def _mark_undone(name) -> None:
	frappe.db.set_value(
		LOG_DOCTYPE, name, {"undone": 1, "undone_by": frappe.session.user, "undone_on": frappe.utils.now()}
	)
