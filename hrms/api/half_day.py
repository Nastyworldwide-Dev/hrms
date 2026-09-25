"""The leave form's AM | PM guidance, from the caller's own shift (25 Sep 2026)."""

import logging
from datetime import datetime, time

import frappe
from frappe.utils import getdate

from hrms.utils.half_day_session import hints_for

logger = logging.getLogger(__name__)


@frappe.whitelist(methods=["GET", "POST"])
def get_half_day_hints(day: str) -> dict:
	"""What AM and PM mean on `day` for the caller: "Start by 13:30" / "Leave at
	13:30". Only the caller's own shift: the form files leave for oneself."""
	from hrms.api import get_current_employee
	from hrms.api.now import default_shift_on
	from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift, get_shift_details

	employee = get_current_employee()
	on = getdate(day)
	noon = datetime.combine(on, time(12))
	found = get_employee_shift(employee, noon)
	shift = (found.get("shift_type") and found["shift_type"].name) if found else None
	shift = shift or default_shift_on(employee, on)
	details = get_shift_details(shift, noon) if shift else None
	hints = hints_for(details.start_datetime if details else None, details.end_datetime if details else None)
	logger.info("[half_day] hints for %s on %s: %s", employee, on, hints.get("shift"))
	return hints
