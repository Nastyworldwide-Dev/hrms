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
from collections import defaultdict
from datetime import date, datetime, time, timedelta

import frappe
from frappe.utils import cint, flt, get_datetime, get_time, getdate

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


def _classify_day(employee, day, default_day_type):
	"""Resolve day_type per work date using the employee's Holiday List and
	their company's configured weekend."""
	logger.info("[ot_calculation] classify day=%s employee=%s default=%s", day, employee, default_day_type)
	holiday_list = None
	company = None
	try:
		holiday_list, company = frappe.db.get_value("Employee", employee, ["holiday_list", "company"]) or (
			None,
			None,
		)
		if not holiday_list and company:
			holiday_list = frappe.db.get_value("Company", company, "default_holiday_list")
	except Exception as exc:
		logger.warning("[ot_calculation] Could not resolve holiday list for %s: %s", employee, exc)

	rest_weekday, off_weekday = _company_weekend(company)

	if holiday_list:
		row = frappe.db.get_value(
			"Holiday",
			{"parent": holiday_list, "holiday_date": day},
			["weekly_off"],
			as_dict=True,
		)
		if row:
			if not row.weekly_off:
				return "public_holiday"
			return "rest" if day.weekday() == rest_weekday else "off"

	weekday = day.weekday()
	if weekday == rest_weekday:
		return "rest"
	if weekday == off_weekday:
		return "off"
	return default_day_type or "normal"


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
					"hours": round(slice_hours, 2),
					"amount": round(slice_hours * hourly_rate * rate, 2),
				}
			)
	return result


def _rate_weighted_hours(bands):
	"""Rate-weighted OT hours = sum(band hours x multiplier). The salary-free figure
	a payroll platform (e.g. Employment Hero) multiplies by its own hourly rate —
	the ERP stops here and never needs the salary."""
	return round(sum(b["hours"] * b["rate"] for b in bands), 2)


def _per_day_ot_hours(employee, start_date, end_date):
	"""Fetch checkins around [start, end], pair IN→OUT sessions, and bucket the
	post-shift-end hours per calendar day, split at midnight. Pre-shift (early
	check-in) time is never overtime. Returns (per_day_hours, per_day_shift)."""
	logger.info("[ot_calculation] per-day OT hours employee=%s %s..%s", employee, start_date, end_date)
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
			"shift_actual_start",
			"shift_actual_end",
			"remote_approval_status",
		],
		order_by="time asc",
	)

	sessions = _pair_sessions(checkins)

	per_day_hours: dict[date, float] = defaultdict(float)
	per_day_shift: dict[date, str] = {}
	for s in sessions:
		if not s.get("shift") or not s.get("shift_end"):
			logger.info("[ot_calculation] Skipping session in=%s — no shift bounds", s.get("first_in"))
			continue
		# OT is post-shift-end only, measured against the REAL shift end (the padded
		# shift_actual_end = end + allow_check_out_after buffer would silently drop OT).
		# Pre-shift (early check-in) time is never counted as overtime.
		real_end = _real_shift_end_for_session(s["shift"], s)
		if not real_end:
			continue
		# OT begins at the shift end, pushed back by however late they clocked in —
		# late arrival is made up first, early arrival never credited. Without this
		# a 9-6 shift clocked 9:30-6:30 (a completed 9h day) was mis-billed 30m OT.
		config = _get_shift_ot_config(s["shift"])
		anchor = s.get("shift_start")
		real_start = (
			_real_shift_start_dt(config["start_time"], anchor.date()) if (config and anchor) else None
		)
		ot_begins = _ot_window_begin(real_start, real_end, s.get("first_in"))
		if s["last_out"] > ot_begins:
			_accumulate_range_by_day(per_day_hours, per_day_shift, s["shift"], ot_begins, s["last_out"])
	return per_day_hours, per_day_shift


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


def _iter_day_ot(employee, start_date, end_date, basic, default_day_type, approved_hours_map=None):
	"""Yield the priced OT for each qualifying day in [start, end], applying
	min-minutes, the daily cap and the running monthly cap. Shared by get_ot_pay
	(sums amounts) and get_ot_breakdown (records the per-day split).

	With approved_hours_map (payroll pricing), a day is priced only when it has
	an approved OT-Pay request, and at no more than its approved hours — the
	daily/monthly caps then apply to those approved hours, not all worked OT."""
	start_date = getdate(start_date)
	end_date = getdate(end_date)
	logger.info("[ot_calculation] iterating OT days employee=%s %s..%s", employee, start_date, end_date)
	per_day_hours, per_day_shift = _per_day_ot_hours(employee, start_date, end_date)

	monthly_ot_hours = 0.0
	cap_month = None
	for day, hours in sorted(per_day_hours.items()):
		if not (start_date <= day <= end_date) or hours <= 0:
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

		if approved_hours_map is not None:
			if day not in approved_hours_map:
				continue
			hours = min(hours, approved_hours_map[day])

		config = _get_shift_ot_config(per_day_shift.get(day))
		if not config:
			# shift missing or overtime disabled for this shift
			continue
		if hours * 60.0 < config["min_minutes"]:
			continue
		if config["daily_cap"] > 0:
			hours = min(hours, config["daily_cap"])
		if config["monthly_cap"] > 0:
			hours = min(hours, max(0.0, config["monthly_cap"] - monthly_ot_hours))
			if hours <= 0:
				continue
		monthly_ot_hours += hours

		resolved_day_type = _classify_day(employee, day, default_day_type)
		hourly_rate = _hourly_rate(basic, config["days_per_month"], config["hours_per_day"])
		bands = _ot_bands_for_day(hours, hourly_rate, resolved_day_type, config)
		amount = round(sum(b["amount"] for b in bands), 2)
		logger.info(
			"[ot_calculation] %s %s ot_hours=%.2f day_type=%s amount=%.2f",
			employee,
			day,
			hours,
			resolved_day_type,
			amount,
		)
		yield {
			"day": day,
			"ot_hours": round(hours, 2),
			"day_type": resolved_day_type,
			"hourly_rate": hourly_rate,
			"bands": bands,
			"amount": amount,
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

	approved = _approved_ot_pay_hours(employee, start_date, end_date)
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
	# Same lateness-adjusted rule as the check-in scan, so the two OT paths agree:
	# a late clock-in pushes OT later; an early one is ignored.
	ot_hours = _ot_hours(real_start, real_end, in_dt, out_dt)

	if ot_hours * 60.0 < config["min_minutes"]:
		logger.info(
			"[ot_calculation] %s %s below min-OT (%.2fh) — no OT", employee, attendance_date, ot_hours
		)
		return _empty_breakdown()
	if config["daily_cap"] > 0:
		ot_hours = min(ot_hours, config["daily_cap"])

	day_type = _classify_day(employee, attendance_date, "normal")
	hourly_rate = _hourly_rate(basic, config["days_per_month"], config["hours_per_day"])
	bands = _ot_bands_for_day(ot_hours, hourly_rate, day_type, config)
	logger.info(
		"[ot_calculation] %s %s ot_hours=%.2f day_type=%s (attendance-centric)",
		employee,
		attendance_date,
		ot_hours,
		day_type,
	)
	return {
		"ot_hours": round(ot_hours, 2),
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


def _pair_sessions(checkins):
	"""Pair check-in rows into IN -> OUT sessions in chronological order."""
	logger.info("[ot_calculation] pairing %d checkin(s)", len(checkins))
	sessions = []
	current = None
	for row in checkins:
		if row.get("remote_approval_status") == "Rejected":
			continue
		log_time = get_datetime(row["time"])
		log_type = row.get("log_type")

		if log_type == "IN":
			if current is not None:
				logger.warning(
					"[ot_calculation] Unpaired IN at %s replaces earlier IN at %s",
					log_time,
					current["first_in"],
				)
			current = {
				"first_in": log_time,
				"shift": row.get("shift"),
				"shift_start": get_datetime(row["shift_actual_start"])
				if row.get("shift_actual_start")
				else None,
				"shift_end": get_datetime(row["shift_actual_end"]) if row.get("shift_actual_end") else None,
			}
		elif log_type == "OUT" and current is not None:
			current["last_out"] = log_time
			if not current.get("shift") and row.get("shift"):
				current["shift"] = row.get("shift")
			if not current["shift_start"] and row.get("shift_actual_start"):
				current["shift_start"] = get_datetime(row["shift_actual_start"])
			if not current["shift_end"] and row.get("shift_actual_end"):
				current["shift_end"] = get_datetime(row["shift_actual_end"])
			sessions.append(current)
			current = None

	logger.info("[ot_calculation] paired %d session(s)", len(sessions))
	return sessions
