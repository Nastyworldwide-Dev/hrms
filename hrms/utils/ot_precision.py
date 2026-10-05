"""Fixed decimal storage representation; source punch intervals stay canonical."""

import logging
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext

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
	minutes_float = float(value or 0) * 60
	if rounding == "down":
		minutes = int(minutes_float + 1e-9)
	elif rounding == "up":
		minutes = -int(-(minutes_float - 1e-9) // 1)
	else:
		minutes = int(minutes_float + 0.5)
	if minutes <= 0:
		return "0m"
	hours, rest = divmod(minutes, 60)
	if not hours:
		return f"{rest}m"
	return f"{hours}h {rest:02d}m"  # same shape as the app's hoursAsTime: "2h 00m", "8h 02m"
