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
