"""OT Request filing window — pure date logic, no Frappe imports.

Unclaimed punch OT used to expire with its calendar month. Per the payroll
vendor cutoff (claims for month M reach payroll until early M+1), filing now
stays open through a grace window: day OT_FILING_GRACE_DAY of the following
month, inclusive. Grace reaches only the immediately-preceding month — older
OT is expired regardless of the day.
"""

import logging
from datetime import date

logger = logging.getLogger(__name__)

# payroll cutoff day of the following month (inclusive) — confirmed with HR 2026-08-12
OT_FILING_GRACE_DAY = 7


def is_within_ot_filing_window(ot_date: date, today: date, grace_day: int = OT_FILING_GRACE_DAY) -> bool:
	if (ot_date.year, ot_date.month) == (today.year, today.month):
		return True
	prev_year, prev_month = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
	in_grace = today.day <= grace_day and (ot_date.year, ot_date.month) == (prev_year, prev_month)
	logger.debug(
		"[filing_window] ot_date=%s today=%s grace_day=%s -> %s", ot_date, today, grace_day, in_grace
	)
	return in_grace
