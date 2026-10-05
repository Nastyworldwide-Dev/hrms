"""Fixed decimal storage representation; source punch intervals stay canonical."""

import logging
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal, InvalidOperation, localcontext

import frappe
from frappe import _

logger = logging.getLogger(__name__)
OT_HOUR_PRECISION = 9
OT_HOUR_FIELDS = {
	"Attendance": ("working_hours", "ot_hours", "ot_rate_weighted_hours"),
	"Attendance Overtime Band": ("hours",),
	"OT Request": ("claimed_hours", "punch_ot_hours"),
}


def stored_ot_hours(value):
	"""Compare like-for-like at decimal(21,9), never by an arbitrary epsilon."""
	logger.debug("[ot_precision] representing OT hours at the persisted decimal scale")
	try:
		with localcontext() as context:
			context.prec = 38
			return Decimal(str(value or 0)).quantize(Decimal("0.000000001"), rounding=ROUND_HALF_UP)
	except (InvalidOperation, ValueError):
		frappe.throw(_("Overtime hours must be a finite number within the supported range."))


def hours_as_words(value, rounding="nearest") -> str:
	"""Hours as a person says them: "8h 52m", "45m", "2h 00m". Never "8.876944444".

	`rounding` keeps a refusal honest: a CAP rounds "down" (never names time the check refuses) and
	a refused CLAIM rounds "up", so a claim above the cap always reads strictly above it
	("8h 53m" against "8h 52m"), never equal. Lists and sheets use "nearest".
	"""
	# ceiling: a claim ONE stored unit (1e-9 h, 3.6 microseconds) above a whole-minute cap reads equal to it;
	# real punches and typed minutes differ by seconds, so it cannot occur. upgrade: if claims ever come from a
	# source finer than a second, compare the nine-decimal values before comparing the words.
	if rounding not in ("nearest", "down", "up"):
		raise ValueError(f"rounding must be nearest, down or up, not {rounding!r}")
	minutes_float = float(value or 0) * 60
	# The stored hours keep nine decimals, so a stored minute (0.016666667 h) is a hair OVER a whole
	# minute and a stored third (0.333333333 h) a hair UNDER 20: the guard is the size of that
	# storage error, a millionth of a minute, not float fuzz.
	if rounding == "down":
		minutes = int(minutes_float + 1e-6)
	elif rounding == "up":
		minutes = -int(-(minutes_float - 1e-6) // 1)
	else:
		minutes = int(minutes_float + 0.5)
	if minutes <= 0:
		return "0m"
	hours, rest = divmod(minutes, 60)
	if not hours:
		return f"{rest}m"
	return f"{hours}h {rest:02d}m"  # same shape as the app's hoursAsTime: "2h 00m", "8h 02m"


def half_hour_claim(value) -> float:
	"""A typed Overtime Pay claim, rounded DOWN to the half hour (owner ruling, 5 Oct 2026).

	HR pays overtime in half-hour steps and the punch cap is already in those steps, so a claim typed
	between them (1.37, 1.6) is cut to the step below (1.0, 1.5). Decimal, not float: a typed 1.5 must
	stay 1.5. Overtime Pay only; Replacement Leave converts the raw hours to days and never calls this.
	"""
	try:
		hours = Decimal(str(value or 0))
	except InvalidOperation:
		frappe.throw(_("Overtime hours must be a finite number within the supported range."))
	if not hours.is_finite() or hours <= 0:
		return 0.0
	return float((hours * 2).to_integral_value(rounding=ROUND_FLOOR) / 2)
