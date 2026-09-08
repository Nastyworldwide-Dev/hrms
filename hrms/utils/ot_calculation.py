"""Overtime pay computation based on Employee Checkin records.

Public API:
    get_ot_pay(employee, start_date, end_date, basic, day_type='normal') -> float

Rates are configured per shift on the Shift Type "Overtime" tab as a table
of hour-range bands per day type (the bands below are the Employment Act 1955
defaults seeded when overtime is enabled):
  - hourly_rate = basic / (working_days_per_month * normal_hours_per_day)  # 26 * 8
  - Normal day:        1.5x for all OT hours
  - Rest day (Sunday): 2.0x for all OT hours
  - Off day  (Saturday): 1.5x first 4 hrs, 2.0x after
  - Public holiday:    3.0x for all OT hours
Each day type can define multiple tiers (e.g. first 8 hrs at 1.5x, beyond at
2.0x); the day's OT hours are priced by walking its bands.

Overtime is only priced for shifts with `enable_overtime` set; the day's
rate bands, hourly-rate divisors, grace and caps are read from that shift.

Sessions are paired IN -> OUT in chronological order. If a session
crosses midnight, OT hours are SPLIT at the date boundary: pre-midnight
hours pay at the IN day's rate, post-midnight hours pay at the next
day's rate (Calendar-Day Split / "Option B").
"""

from __future__ import annotations

import logging
from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import frappe
from frappe.utils import cint, flt, get_datetime, get_time, getdate

from hrms.utils.ot_precision import stored_ot_hours

logger = logging.getLogger(__name__)

WORKING_DAYS_PER_MONTH = 26
HOURS_PER_DAY = 8

# Maps the day types resolved by _classify_day to the Shift Overtime Rate
# "Day Type" select stored on the shift.
DAY_TYPE_LABELS = {
	"normal": "Normal Day",
	"rest": "Rest Day",
	"off": "Off Day",
	"public_holiday": "Public Holiday",
}

# Employment Act 1955 default bands, keyed by Day Type label.
# Each band is (from_hour, from_minute, to_hour, to_minute, rate).
DEFAULT_OT_RATE_BANDS = {
	"Normal Day": [(0, 0, 23, 59, 1.5)],
	"Rest Day": [(0, 0, 23, 59, 2.0)],
	"Off Day": [(0, 0, 4, 0, 1.5), (4, 0, 23, 59, 2.0)],
	"Public Holiday": [(0, 0, 23, 59, 3.0)],
}


def round_ot_pay_hours(hours) -> float:
	"""Round worked OT to HR's 30-minute pay bands. OT PAY ONLY — Replacement Leave
	converts the RAW hours to days (4h=½, 8h=1) and never passes through here.

	By the minutes past the whole hour:
	  * 0-29 min  -> drop to :00
	  * 30-49 min -> :30 (half hour)
	  * 50-59 min -> round up to the next :00
	So 1h29m pays 1.0h, 1h30m-1h49m pays 1.5h, and 1h50m pays 2.0h.
	"""
	total = flt(hours)
	if total <= 0:
		return 0.0
	whole, minutes = divmod(round(total * 60), 60)
	rounded = float(whole) if minutes < 30 else (whole + 0.5 if minutes < 50 else float(whole + 1))
	logger.debug("[ot_calculation] OT-pay round %.3fh -> %.1fh (%dh%02dm)", total, rounded, whole, minutes)
	return rounded


def replacement_leave_days(hours, hours_per_day=8) -> float:
	"""Replacement leave earned by ONE working day's OT, in whole half-day blocks:
	4 h = ½ day, 8 h = 1 day, 12 h = 1.5 day, under 4 h = 0. Computed and stored PER
	DAY — NOT banked, NOT accumulated: a short day earns nothing and never carries to
	the next. `hours_per_day` is HR's full-day ratio (default 8); half a day is half
	of it (4 h), and the remainder inside a block is dropped (6 h still = ½ day)."""
	half = flt(hours_per_day) / 2.0
	if not hours or half <= 0:
		return 0.0
	blocks = int(flt(hours) / half)  # whole half-day blocks; the partial block is lost
	result = blocks * 0.5
	logger.debug("[ot_calculation] RL %.2fh (half=%.1f) -> %s day(s)", flt(hours), half, result)
	return result


def _hourly_rate(basic, days_per_month=WORKING_DAYS_PER_MONTH, hours_per_day=HOURS_PER_DAY):
	if not basic or basic <= 0 or days_per_month <= 0 or hours_per_day <= 0:
		return 0.0
	return basic / (days_per_month * hours_per_day)


def _get_shift_ot_config(shift_name):
	"""Read the Overtime tab settings off a Shift Type. Returns None when the
	shift is missing or overtime is disabled (so no OT is priced)."""
	if not shift_name:
		return None

	shift = frappe.get_cached_doc("Shift Type", shift_name)
	if not shift or not shift.enable_overtime:
		return None

	def _or_default(value, default):
		# fall back only when unset (None); a configured 0 is honoured
		return default if value is None else value

	label_to_key = {label: key for key, label in DAY_TYPE_LABELS.items()}
	bands: dict[str, list] = defaultdict(list)
	for row in shift.overtime_rates:
		key = label_to_key.get(row.day_type)
		if not key:
			continue
		from_hours = (row.from_hour or 0) + (row.from_minute or 0) / 60.0
		to_hours = (row.to_hour or 0) + (row.to_minute or 0) / 60.0
		bands[key].append((from_hours, to_hours, flt(row.rate)))
	for key in bands:
		bands[key].sort()

	return {
		"min_minutes": cint(shift.minimum_overtime_minutes),
		"days_per_month": _or_default(shift.overtime_working_days_per_month, WORKING_DAYS_PER_MONTH),
		"hours_per_day": _or_default(shift.overtime_normal_hours_per_day, HOURS_PER_DAY),
		"bands": dict(bands),
		"daily_cap": flt(shift.daily_overtime_cap_hours),
		"monthly_cap": flt(shift.monthly_overtime_cap_hours),
		# Shift window — OT is measured against the *real* shift end (not the padded
		# shift_actual_end = end + allow_check_out_after buffer, which silently ate OT).
		"start_time": shift.start_time,
		"end_time": shift.end_time,
		"allow_check_out_after": cint(shift.allow_check_out_after_shift_end_time),
		"checkin_policy": shift.determine_check_in_and_check_out,
	}


def _real_shift_end_dt(start_time, end_time, work_date):
	"""Real shift-end datetime for a work date, ignoring the check-out grace buffer.
	Handles overnight shifts (end <= start rolls to the next calendar day)."""
	start_t = get_time(start_time)
	end_t = get_time(end_time)
	end_dt = datetime.combine(work_date, end_t)
	if end_t <= start_t:
		end_dt += timedelta(days=1)
	logger.debug("[ot_calculation] real shift end %s..%s on %s -> %s", start_t, end_t, work_date, end_dt)
	return end_dt


def _real_shift_start_dt(start_time, work_date) -> datetime:
	"""Real shift-start datetime for a work date — the configured start, with no
	early-arrival grace. Overtime is measured from here, never from an early punch."""
	return datetime.combine(work_date, get_time(start_time))


def _ot_window_begin(real_start, real_end, in_dt) -> datetime:
	"""When overtime begins: the shift end, pushed later by however late the
	employee clocked in. A late arrival owes that time back before OT counts; an
	early arrival is never credited (lateness floored at 0).

	This is the rule HR stated — OT = total hours worked - shift length — expressed
	as a start time, so both OT paths (the day-level check-in scan and the
	per-attendance one) price identically. The old code measured raw time past the
	shift end, which handed every late-in employee overtime they had not yet earned:
	a 9-6 shift clocked 9:30-6:30 is a completed 9h day, not 30 minutes of OT."""
	late_seconds = 0.0
	if real_start and in_dt and in_dt > real_start:
		late_seconds = (in_dt - real_start).total_seconds()
	return real_end + timedelta(seconds=late_seconds)


def _ot_hours(real_start, real_end, in_dt, out_dt) -> float:
	"""Overtime hours for one worked window, through the shared lateness-adjusted
	rule. Zero when there is no clock-out or it does not pass the OT start."""
	if not out_dt:
		return 0.0
	return max(0.0, (out_dt - _ot_window_begin(real_start, real_end, in_dt)).total_seconds() / 3600.0)


def _real_shift_end_for_session(shift_name, session) -> datetime | None:
	"""The real shift end a session's OT is measured against.

	From the shift's CONFIGURED start/end anchored on the session's own shift
	start — the same derivation get_shift_ot_breakdown uses, so the two OT
	paths cannot disagree. The old derivation subtracted the CURRENT
	allow_check_out_after buffer from the punch-time shift_actual_end
	snapshot, so raising that buffer 60 -> 240 silently inflated every
	HISTORICAL session's OT by 3h. Shift start/end changes carry no such
	risk: ShiftType.validate refuses a start_time change while unprocessed
	check-ins exist.

	Falls back to snapshot-minus-buffer when the session has no shift_start
	(older rows), and to None when the shift itself is gone.
	"""
	config = _get_shift_ot_config(shift_name)
	anchor = session.get("shift_start")
	if config and anchor:
		return _real_shift_end_dt(config["start_time"], config["end_time"], anchor.date())

	buffer_minutes = frappe.db.get_value("Shift Type", shift_name, "allow_check_out_after_shift_end_time")
	if buffer_minutes is None:
		logger.warning("[ot_calculation] shift %s missing — cannot resolve real end", shift_name)
		return None
	return session["shift_end"] - timedelta(minutes=cint(buffer_minutes))


_WEEKDAY_INDEX = {
	"Monday": 0,
	"Tuesday": 1,
	"Wednesday": 2,
	"Thursday": 3,
	"Friday": 4,
	"Saturday": 5,
	"Sunday": 6,
}

#: Historical hardcode, kept as the blank-field default so every existing
#: company prices exactly as before.
DEFAULT_REST_WEEKDAY = 6  # Sunday
DEFAULT_OFF_WEEKDAY = 5  # Saturday


def _company_weekend(company) -> tuple[int, int]:
	"""(rest_weekday, off_weekday) for a company, tolerating an unmigrated schema.

	Rest day pays 2.0x against the off day's 1.5x first-band, so hardcoding
	Sunday/Saturday was wrong money for any Friday-Saturday-weekend entity
	(Malaysia's east-coast states, KSA). Configured per company on
	`hr_weekly_rest_day` / `hr_weekly_off_day`; blank keeps the historical
	Sunday/Saturday. A missing column degrades to the defaults — the same
	fail-open shape as hrms.utils.timezone._optional_timezone_field, and for
	the same reason: pricing OT must not crash on a half-finished migrate.
	"""
	if not company:
		return DEFAULT_REST_WEEKDAY, DEFAULT_OFF_WEEKDAY
	try:
		rest_name, off_name = frappe.db.get_value(
			"Company", company, ["hr_weekly_rest_day", "hr_weekly_off_day"]
		) or (None, None)
	except Exception:
		logger.warning("[ot_calculation] weekend fields unavailable — has the custom-field sync run?")
		return DEFAULT_REST_WEEKDAY, DEFAULT_OFF_WEEKDAY
	return (
		_WEEKDAY_INDEX.get(rest_name, DEFAULT_REST_WEEKDAY),
		_WEEKDAY_INDEX.get(off_name, DEFAULT_OFF_WEEKDAY),
	)


def _classify_day(employee, day, default_day_type, shift=None):
	"""Resolve the work date from the same applicable calendar as Shift Type.

	Company weekend settings distinguish listed weekly-off rows; they never
	create a holiday absent from the applicable calendar.
	"""
	from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

	day = getdate(day)
	logger.info("[ot_calculation] classify day=%s employee=%s shift=%s", day, employee, shift)
	holiday_list = frappe.db.get_value("Shift Type", shift, "holiday_list") if shift else None
	if not holiday_list:
		holiday_list = get_holiday_list_for_employee(employee, False, as_on=day)
	if not holiday_list:
		logger.warning("[ot_calculation] no applicable holiday list for work date %s", day)
		return "normal"
	row = frappe.db.get_value(
		"Holiday", {"parent": holiday_list, "holiday_date": day}, ["weekly_off"], as_dict=True
	)
	if not row:
		return "normal"
	if not cint(row.weekly_off):
		return "public_holiday"
	company = frappe.db.get_value("Employee", employee, "company")
	rest_weekday, _ = _company_weekend(company)
	return "rest" if day.weekday() == rest_weekday else "off"


def _ot_bands_for_day(ot_hours, hourly_rate, day_type, config):
	"""Split a day's OT hours across the day type's rate bands, returning one
	entry per non-empty band: {day_type, rate, hours, amount}. Band *hours* are
	computed even when hourly_rate is 0 (no basic salary resolved yet), so the
	rate breakdown is always available — only the amount depends on basic.
	Bands are (from_hours, to_hours, rate); the last is open-ended."""
	logger.info("[ot_calculation] band-split day_type=%s ot_hours=%.2f", day_type, ot_hours)
	if ot_hours <= 0:
		return []

	bands = config.get("bands", {}).get(day_type, [])
	if not bands:
		logger.warning(
			"[ot_calculation] No overtime bands configured for day_type=%s — %.2fh unpriced",
			day_type,
			ot_hours,
		)
		return []

	result = []
	last = len(bands) - 1
	for i, (from_hours, to_hours, rate) in enumerate(bands):
		upper = ot_hours if i == last else min(ot_hours, to_hours)
		slice_hours = upper - from_hours
		if slice_hours > 0:
			result.append(
				{
					"day_type": day_type,
					"rate": rate,
					"hours": round(slice_hours, 2) if day_type == "normal" else slice_hours,
					"amount": round(slice_hours * hourly_rate * rate, 2),
				}
			)
	return result


def _rate_weighted_hours(bands):
	"""Rate-weighted OT hours = sum(band hours x multiplier). The salary-free figure
	a payroll platform (e.g. Employment Hero) multiplies by its own hourly rate —
	the ERP stops here and never needs the salary."""
	total = sum(b["hours"] * b["rate"] for b in bands)
	return round(total, 2) if all(b["day_type"] == "normal" for b in bands) else total


def _per_day_contributions(employee, start_date, end_date):
	"""Eligible worked overtime per calendar day, kept PER SHIFT in work order.

	Returns {day: [{"shift": name, "hours": h}, ...]}: one entry per shift the
	day was worked under, consecutive sessions on the same shift merged, in the
	order they were worked. Keeping the split is the point — a day worked
	across two shifts (a normal-day morning, a rest-day afternoon) is priced by
	EACH shift's own calendar and bands, never by whichever shift wrote last.
	Pre-shift (early check-in) time is never overtime; a holiday interval is
	counted whole (see _session_ot_slices)."""
	logger.info(
		"[ot_calculation] per-day OT contributions employee=%s %s..%s", employee, start_date, end_date
	)
	fetch_start = start_date - timedelta(days=1)
	fetch_end = end_date + timedelta(days=1)
	checkins = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ["between", [f"{fetch_start} 00:00:00", f"{fetch_end} 23:59:59"]],
		},
		fields=[
			"name",
			"time",
			"log_type",
			"shift",
			"shift_start",
			"shift_end",
			"shift_actual_start",
			"shift_actual_end",
			"remote_approval_status",
			"requires_remote_approval",
			"skip_auto_attendance",
			"offshift",
		],
		order_by="time asc",
	)

	configs = {shift: _get_shift_ot_config(shift) for shift in {row.get("shift") for row in checkins}}
	policies = {shift: config.get("checkin_policy") for shift, config in configs.items() if config}
	sessions = _pair_sessions(checkins, policies)
	per_day: dict[date, list[dict]] = defaultdict(list)
	for session in sessions:
		shift = session.get("shift")
		config = configs.get(shift)
		if not config:
			continue
		for day, hours, _ in _session_ot_slices(employee, session, config):
			entries = per_day[day]
			# One entry per shift per day, in first-worked order: a shift left
			# and resumed later the same day is still one contribution, so its
			# daily cap applies to the whole of it.
			for entry in entries:
				if entry["shift"] == shift:
					entry["hours"] += hours
					break
			else:
				entries.append({"shift": shift, "hours": hours})
	return per_day


def _per_day_ot_hours(employee, start_date, end_date):
	"""Day totals and each day's DOMINANT shift — the single-shift view of
	_per_day_contributions, kept for callers that only need a shift to
	classify a whole day by. Returns (per_day_hours, per_day_shift)."""
	return _maps_from_contributions(_per_day_contributions(employee, start_date, end_date))


def _maps_from_contributions(contributions):
	per_day_hours: dict[date, float] = defaultdict(float)
	per_day_shift: dict[date, str] = {}
	for day, entries in contributions.items():
		per_day_hours[day] = sum(entry["hours"] for entry in entries)
		# ceiling: a mixed day is classified by the shift it was mostly worked
		# under, upgrade: per-shift approved reservations if HR ever claims a
		# day split across calendars.
		per_day_shift[day] = max(entries, key=lambda entry: entry["hours"])["shift"]
	return per_day_hours, per_day_shift


def _contributions_from_maps(per_day_hours, per_day_shift):
	"""The inverse view, for callers that only know a day total and one shift."""
	return {day: [{"shift": per_day_shift.get(day), "hours": hours}] for day, hours in per_day_hours.items()}


def _session_ot_slices(employee, session, config):
	"""Calendar-day OT slices shared by raw scans and Attendance breakdowns."""
	shift = session["shift"]
	anchor = session.get("shift_start")
	real_end = _real_shift_end_for_session(shift, session) if session.get("shift_end") else None
	real_start = _real_shift_start_dt(config["start_time"], anchor.date()) if anchor else None
	ot_begins = (
		_ot_window_begin(real_start, real_end, session.get("shift_first_in", session["first_in"]))
		if real_end
		else None
	)
	cursor = session["first_in"]
	logger.debug("[ot_calculation] slicing eligible worked interval by calendar day")
	while cursor < session["last_out"]:
		slice_end = min(session["last_out"], datetime.combine(cursor.date() + timedelta(days=1), time.min))
		day_type = _classify_day(employee, cursor.date(), "normal", shift=shift)
		# Scheduled weekday breaks and the shift end never erase holiday work.
		start = cursor if day_type != "normal" else max(cursor, ot_begins or slice_end)
		if start < slice_end:
			yield cursor.date(), (slice_end - start).total_seconds() / 3600, day_type
		cursor = slice_end


def _approved_ot_pay_hours(employee, start_date, end_date):
	"""OT is paid only when explicitly requested and approved: map of
	{ot_date: claimed whole hours} from submitted OT-Pay OT Requests."""
	rows = frappe.get_all(
		"OT Request",
		filters={
			"employee": employee,
			"docstatus": 1,
			# A rejected request reaches docstatus 1 like any other decision
			# (rejecting is a decision, not a cancellation), so without this the
			# salary formula would price the hours a Reject was refusing. Same
			# guard the replacement-leave bank carries in ot_request.py.
			"status": ("!=", "Rejected"),
			"compensation": "Overtime Pay",
			"ot_date": ["between", [start_date, end_date]],
		},
		fields=["ot_date", "claimed_hours"],
	)
	approved = {getdate(r.ot_date): flt(r.claimed_hours) for r in rows}
	logger.info("[ot_calculation] approved OT-Pay days employee=%s: %s", employee, len(approved))
	return approved


def _iter_day_ot(
	employee,
	start_date,
	end_date,
	basic,
	default_day_type,
	approved_hours_map=None,
	*,
	apply_monthly_cap=True,
):
	"""Yield the priced OT for each qualifying day in [start, end].

	Every contribution a day was worked under (one per shift, in work order)
	is classified with its own shift's calendar, qualified against its own
	minimum, capped by its own daily cap and the running monthly cap when it
	is weekday work, and priced by its own bands. The day's row sums them and
	says how much was weekday work (`normal_hours`) and how much holiday work
	(`nonworking_hours`), so a claim cap can be applied to the weekday part
	alone. Shared by get_ot_pay (sums amounts), get_ot_breakdown (records the
	per-day split) and get_ot_claim_capacity.

	With approved_hours_map (payroll pricing), a day is priced only when it has
	an approved OT-Pay request, at no more than its approved hours — spent
	across the day's contributions in work order — and the daily/monthly caps
	then apply to those approved hours, not all worked OT."""
	start_date = getdate(start_date)
	end_date = getdate(end_date)
	logger.info("[ot_calculation] iterating OT days employee=%s %s..%s", employee, start_date, end_date)
	# Count from the calendar-month boundary even when the caller asks for one
	# day or a payroll period starting mid-month. Only the output is sliced.
	cap_start = start_date.replace(day=1) if apply_monthly_cap else start_date
	contributions = _per_day_contributions(employee, cap_start, end_date)

	monthly_ot_hours = 0.0
	cap_month = None
	for day in sorted(contributions):
		if not (cap_start <= day <= end_date):
			continue

		# The cap is MONTHLY, so the accumulator resets on a month boundary.
		# Accumulated across the whole queried range it silently tightened for
		# any range spanning two months — a 26th-to-25th payroll period reached
		# the cap once for what are two distinct months' entitlements.
		# CALENDAR month by decision (2026-08-19): the 16th-to-15th payroll
		# cycle governs only the filing window (utils/filing_window.py); the
		# cap keeps the counting the older branches always had.
		if (day.year, day.month) != cap_month:
			cap_month = (day.year, day.month)
			monthly_ot_hours = 0.0

		approved_left = None
		if approved_hours_map is not None:
			approved_left = max(0.0, approved_hours_map.get(day, 0))

		# One contribution per shift, whatever the producer handed over: a
		# shift's daily cap must see the whole of what it was worked that day.
		merged: list[dict] = []
		for entry in contributions[day]:
			for known in merged:
				if known["shift"] == entry["shift"]:
					known["hours"] += entry["hours"]
					break
			else:
				merged.append({"shift": entry["shift"], "hours": entry["hours"]})

		priced = []
		for entry in merged:
			hours = entry["hours"]
			if hours <= 0:
				continue
			config = _get_shift_ot_config(entry["shift"])
			if not config:
				# shift missing or overtime disabled for this shift
				continue
			day_type = _classify_day(employee, day, default_day_type, shift=entry["shift"])
			nonworking = day_type != "normal"
			if not nonworking and hours * 60.0 < config["min_minutes"]:
				continue
			# The minimum qualifies WORKED overtime. A smaller approved claim or
			# remaining monthly allowance must not be tested against it a second time.
			if approved_left is not None:
				hours = min(hours, approved_left)
				if hours <= 0:
					continue
			if not nonworking and config["daily_cap"] > 0:
				hours = min(hours, config["daily_cap"])
			if not nonworking and apply_monthly_cap and config["monthly_cap"] > 0:
				hours = min(hours, max(0.0, config["monthly_cap"] - monthly_ot_hours))
				if hours <= 0:
					continue
			# Approved hours are spent on what was actually PRICED: the part a
			# shift's own cap trimmed stays available to the day's next shift.
			if approved_left is not None:
				approved_left -= hours
			if not nonworking:
				monthly_ot_hours += hours
			hourly_rate = _hourly_rate(basic, config["days_per_month"], config["hours_per_day"])
			bands = _ot_bands_for_day(hours, hourly_rate, day_type, config)
			priced.append(
				{
					"shift": entry["shift"],
					"day_type": day_type,
					"hours": hours,
					"nonworking": nonworking,
					"monthly_cap": 0 if nonworking else config["monthly_cap"],
					"hourly_rate": hourly_rate,
					"bands": bands,
					"amount": round(sum(b["amount"] for b in bands), 2),
				}
			)
		if not priced or day < start_date:
			continue

		normal_hours = sum(p["hours"] for p in priced if not p["nonworking"])
		nonworking_hours = sum(p["hours"] for p in priced if p["nonworking"])
		dominant = max(priced, key=lambda p: p["hours"])
		amount = round(sum(p["amount"] for p in priced), 2)
		logger.info(
			"[ot_calculation] %s %s normal=%.2fh nonworking=%.2fh contributions=%d amount=%.2f",
			employee,
			day,
			normal_hours,
			nonworking_hours,
			len(priced),
			amount,
		)
		yield {
			"day": day,
			# The TIGHTEST weekday cap on the day: the capacity replay bounds
			# future headroom by this figure, and a looser shift on the same day
			# must not hide a tighter one. 0 means no cap.
			# ceiling: one monthly accumulator shared by every shift, upgrade:
			# per-shift accumulators if HR ever caps two shifts differently
			# for one person in one month.
			"monthly_cap": min(
				(p["monthly_cap"] for p in priced if not p["nonworking"] and p["monthly_cap"] > 0),
				default=0,
			),
			"unrounded_ot_hours": normal_hours + nonworking_hours,
			# Weekday work keeps its two-decimal report figure; holiday work is exact.
			"ot_hours": round(normal_hours, 2) + nonworking_hours,
			"normal_hours": normal_hours,
			"nonworking_hours": nonworking_hours,
			# One type when the day was one kind of work; otherwise the kind it
			# was mostly worked as, with the split carried alongside.
			"day_type": dominant["day_type"],
			"hourly_rate": priced[0]["hourly_rate"],
			"bands": [band for p in priced for band in p["bands"]],
			"amount": amount,
			"contributions": [
				{"shift": p["shift"], "day_type": p["day_type"], "hours": p["hours"]} for p in priced
			],
		}


def get_ot_pay(employee, start_date, end_date, basic, day_type="normal"):
	logger.info(
		"[ot_calculation] get_ot_pay employee=%s start=%s end=%s basic=%s",
		employee,
		start_date,
		end_date,
		basic,
	)
	if not employee or not basic:
		return 0.0

	# Earlier approved claims consume this calendar month's allowance even
	# when their payment is outside the requested payroll interval.
	approved = _approved_ot_pay_hours(employee, getdate(start_date).replace(day=1), getdate(end_date))
	total_pay = sum(
		d["amount"]
		for d in _iter_day_ot(employee, start_date, end_date, basic, day_type, approved_hours_map=approved)
	)
	logger.info("[ot_calculation] total_pay employee=%s -> %.2f", employee, round(total_pay, 2))
	return round(total_pay, 2)


def get_ot_breakdown(employee, start_date, end_date, basic, day_type="normal"):
	"""Per-day working/OT breakdown for reporting and the Attendance controller.

	Returns {date: {ot_hours, day_type, bands: [{day_type, rate, hours, amount}],
	ot_amount}}. Unlike get_ot_pay this does NOT require basic — band hours are
	always populated; amounts are 0 until a basic salary is resolved.
	"""
	logger.info(
		"[ot_calculation] get_ot_breakdown employee=%s start=%s end=%s", employee, start_date, end_date
	)
	if not employee:
		return {}

	breakdown = {}
	for d in _iter_day_ot(employee, start_date, end_date, basic or 0, day_type):
		breakdown[d["day"]] = {
			"ot_hours": d["ot_hours"],
			"day_type": d["day_type"],
			"bands": d["bands"],
			"rate_weighted_hours": _rate_weighted_hours(d["bands"]),
			"ot_amount": d["amount"],
		}
	return breakdown


def get_day_ot_breakdown(employee, day, basic=0):
	"""OT breakdown for a single day — used by the Attendance controller.

	basic is optional: with salary held on the payroll platform, the ERP stops
	at hours, so callers pass no basic and read ot_hours + bands (hours x rate)
	+ rate_weighted_hours. ot_amount is 0 unless a basic is supplied.
	"""
	day = getdate(day)
	logger.info("[ot_calculation] get_day_ot_breakdown employee=%s day=%s", employee, day)
	return get_ot_breakdown(employee, day, day, basic).get(day) or _empty_breakdown()


def get_ot_claim_capacity(employee, day, compensation, *, exclude_request=None):
	"""Claim capacity, distinct from a raw-work report's chronological monthly cap.

	Only approved OT-Pay claims reserve the pay allowance. Include the whole
	month so backdated filing cannot displace a later approved claim. The caller
	may exclude only its own persisted document during controller revalidation;
	whitelisted summary endpoints never accept an exclusion from the client.
	Replacement Leave retains its existing raw-work behavior pending HR policy.
	"""
	day = getdate(day)
	if compensation != "Overtime Pay":
		return {
			"hours": float(stored_ot_hours(get_day_ot_breakdown(employee, day)["ot_hours"])),
			"monthly_remaining": None,
		}
	worked = next(_iter_day_ot(employee, day, day, 0, "normal", apply_monthly_cap=False), None)
	if not worked:
		return {"hours": 0.0, "monthly_remaining": None, "uncapped_hours": 0.0}
	# HR's holiday entitlement is uncapped and exact; only the weekday part of
	# a day competes for the monthly allowance. A day worked across a rest-day
	# shift and a normal-day shift therefore caps its normal hours alone.
	uncapped = stored_ot_hours(worked["nonworking_hours"])
	if worked["normal_hours"] <= 0:
		return {
			"hours": float(uncapped),
			"monthly_remaining": None,
			"day_type": worked["day_type"],
			"uncapped_hours": float(uncapped),
		}
	# Round the earned amount before clipping: rounding a remaining allowance
	# afterwards can raise a claim above the configured monthly maximum.
	hours = round_ot_pay_hours(worked["normal_hours"])
	cap = worked["monthly_cap"]
	month_start = day.replace(day=1)
	month_end = day.replace(day=monthrange(day.year, day.month)[1])
	filters = {
		"employee": employee,
		"docstatus": 1,
		"status": ("!=", "Rejected"),
		"compensation": "Overtime Pay",
		"ot_date": ["between", [month_start, month_end]],
	}
	if exclude_request:
		filters["name"] = ("!=", exclude_request)
	approved = frappe.get_all("OT Request", filters=filters, fields=["ot_date", "claimed_hours"])
	if approved:
		_, approved_shifts = _per_day_ot_hours(employee, month_start, month_end)
		# HR's uncapped holiday entitlement is separate from the weekday cap:
		# neither a holiday reservation nor its payout consumes weekday hours.
		approved = [
			row
			for row in approved
			if _classify_day(
				employee, getdate(row.ot_date), "normal", shift=approved_shifts.get(getdate(row.ot_date))
			)
			== "normal"
		]
	remaining = None
	if cap > 0:
		reserved = sum(Decimal(str(max(0.0, flt(row.claimed_hours)))) for row in approved)
		remaining = max(Decimal(0), Decimal(str(cap)) - reserved)
	# An earlier high-cap (or unlimited) shift must not displace a later
	# approval made under a smaller cap. Replay existing payroll consumption
	# and retain enough headroom to preserve every later paid date.
	if any(getdate(row.ot_date) > day for row in approved):
		approved_by_day = defaultdict(float)
		for row in approved:
			approved_by_day[getdate(row.ot_date)] += max(0.0, flt(row.claimed_hours))
		consumed = Decimal(0)
		for priced in _iter_day_ot(employee, month_start, month_end, 0, "normal", approved_by_day):
			consumed += Decimal(str(priced["normal_hours"]))
			if priced["day"] > day and priced["monthly_cap"] > 0:
				headroom = max(Decimal(0), Decimal(str(priced["monthly_cap"])) - consumed)
				remaining = headroom if remaining is None else min(remaining, headroom)
	if remaining is not None:
		remaining = float(remaining)
		hours = min(hours, remaining)
	logger.info(
		"[ot_calculation] claim capacity date=%s compensation=%s hours=%.3f", day, compensation, hours
	)
	# Claims and UI previews share the physical decimal representation; raw
	# worked intervals above remain exact until their own persistence boundary.
	return {
		"hours": float(stored_ot_hours(hours) + uncapped),
		"monthly_remaining": float(stored_ot_hours(remaining)) if remaining is not None else None,
		"day_type": worked["day_type"],
		"uncapped_hours": float(uncapped),
	}


def _empty_breakdown():
	return {"ot_hours": 0.0, "day_type": None, "bands": [], "rate_weighted_hours": 0.0, "ot_amount": 0.0}


def get_shift_ot_breakdown(employee, shift, attendance_date, out_time, in_time=None, basic=0):
	"""Per-attendance OT priced from the attendance's OWN shift + last check-out.

	OT = total hours worked - shift length: the shift end pushed later by however
	late they clocked in (early arrival never credited), then out_time beyond that.
	Pass in_time so the lateness is applied; without it this degrades to raw
	post-shift-end. Unlike the day-level checkin scan (get_day_ot_breakdown), this
	reads the attendance's own shift and in/out, so it is robust when the day has
	duplicate/reassigned attendances. Returns the same
	shape: {ot_hours, day_type, bands, rate_weighted_hours, ot_amount}. Salary lives
	on the payroll platform, so basic defaults to 0 and amounts stay 0."""
	attendance_date = getdate(attendance_date)
	logger.info(
		"[ot_calculation] get_shift_ot_breakdown employee=%s shift=%s date=%s out=%s",
		employee,
		shift,
		attendance_date,
		out_time,
	)
	if not (shift and out_time):
		return _empty_breakdown()

	config = _get_shift_ot_config(shift)
	if not config:
		# shift missing or overtime disabled
		return _empty_breakdown()

	out_dt = get_datetime(out_time)
	real_start = _real_shift_start_dt(config["start_time"], attendance_date)
	real_end = _real_shift_end_dt(config["start_time"], config["end_time"], attendance_date)
	in_dt = get_datetime(in_time) if in_time else None
	day_type = _classify_day(employee, attendance_date, "normal", shift=shift)
	if day_type != "normal" and not in_dt:
		return _empty_breakdown()
	rows = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee, "shift": shift, "time": ["between", [in_dt or real_start, out_dt]]},
		fields=[
			"time",
			"log_type",
			"shift",
			"shift_start",
			"shift_actual_start",
			"shift_actual_end",
			"remote_approval_status",
			"requires_remote_approval",
			"skip_auto_attendance",
			"offshift",
		],
		order_by="time asc",
	)
	if rows:
		sessions = _pair_sessions(rows, {shift: config.get("checkin_policy")})
	else:
		# Retain manually entered Attendance's trusted timestamps when it has
		# no source checkins. Existing but ineligible punches never use fallback.
		sessions = [
			{
				"first_in": in_dt or real_start,
				"last_out": out_dt,
				"shift": shift,
				"shift_start": real_start,
				"shift_end": real_end,
			}
		]
	buckets = defaultdict(float)
	types = {}
	for session in sessions:
		for day, hours, resolved_type in _session_ot_slices(employee, session, config):
			buckets[day] += hours
			types[day] = resolved_type
	hourly_rate = _hourly_rate(basic, config["days_per_month"], config["hours_per_day"])
	bands = []
	ot_hours = 0.0
	for day, hours in sorted(buckets.items()):
		if types[day] == "normal":
			if hours * 60 < config["min_minutes"]:
				continue
			if config["daily_cap"] > 0:
				hours = min(hours, config["daily_cap"])
		ot_hours += hours
		bands.extend(_ot_bands_for_day(hours, hourly_rate, types[day], config))
	return {
		"ot_hours": round(ot_hours, 2) if all(t == "normal" for t in types.values()) else ot_hours,
		"day_type": day_type,
		"bands": bands,
		"rate_weighted_hours": _rate_weighted_hours(bands),
		"ot_amount": round(sum(b["amount"] for b in bands), 2),
	}


def _accumulate_range_by_day(buckets, shift_buckets, shift_name, start_dt, end_dt):
	"""Add (start_dt, end_dt) duration to `buckets`, splitting at midnight.
	Records the contributing shift per day in `shift_buckets`."""
	if end_dt <= start_dt:
		return
	cursor = start_dt
	while cursor < end_dt:
		next_midnight = datetime.combine(cursor.date() + timedelta(days=1), time.min)
		slice_end = min(next_midnight, end_dt)
		hours = (slice_end - cursor).total_seconds() / 3600.0
		if hours > 0:
			buckets[cursor.date()] += hours
			shift_buckets[cursor.date()] = shift_name
			logger.info(
				"[ot_calculation] slice %s += %.2fh (%s -> %s)",
				cursor.date(),
				hours,
				cursor,
				slice_end,
			)
		cursor = slice_end


def _is_eligible_checkin(row):
	"""A refused or pending punch remains a boundary, never worked evidence."""
	logger.debug("[ot_calculation] checking punch eligibility")
	return (
		row.get("remote_approval_status") in (None, "", "Approved")
		and not cint(row.get("requires_remote_approval"))
		and not cint(row.get("skip_auto_attendance"))
		and not cint(row.get("offshift"))
	)


def _pair_sessions(checkins, policies=None):
	"""Eligible, positive IN/OUT intervals using each shift's log interpretation.

	Strict policy keeps the first IN until an OUT, matching native attendance.
	Alternating policy ignores log_type. Ineligible evidence breaks an open pair
	so removing a refused/pending punch cannot fabricate a longer interval.
	"""
	logger.info("[ot_calculation] pairing %d checkin(s)", len(checkins))
	sessions = []
	current = None
	for row in checkins:
		if not _is_eligible_checkin(row):
			current = None
			continue
		log_time = get_datetime(row["time"])
		shift = row.get("shift") or (current or {}).get("shift")
		anchor = row.get("shift_start") or row.get("shift_actual_start")
		anchor = get_datetime(anchor) if anchor else None
		if current and (
			(current.get("shift") and shift and current["shift"] != shift)
			or (anchor and current.get("shift_start") and anchor != current["shift_start"])
		):
			current = None
		policy = (policies or {}).get(shift)
		log_type = row.get("log_type")
		if policy == "Alternating entries as IN and OUT during the same shift":
			log_type = "OUT" if current else "IN"
		if log_type == "IN" and current is None:
			current = {
				"first_in": log_time,
				"shift": shift,
				"shift_start": anchor,
				"shift_end": get_datetime(row["shift_actual_end"]) if row.get("shift_actual_end") else None,
			}
		elif log_type == "OUT" and current is not None:
			current["last_out"] = log_time
			current["shift"] = current.get("shift") or shift
			current["shift_start"] = current.get("shift_start") or anchor
			if not current["shift_end"] and row.get("shift_actual_end"):
				current["shift_end"] = get_datetime(row["shift_actual_end"])
			if log_time > current["first_in"]:
				sessions.append(current)
			current = None
	first_ins = {}
	for session in sessions:
		key = (session["shift"], session["shift_start"] or session["first_in"].date())
		session["shift_first_in"] = first_ins.setdefault(key, session["first_in"])
	logger.info("[ot_calculation] paired %d session(s)", len(sessions))
	return sessions
