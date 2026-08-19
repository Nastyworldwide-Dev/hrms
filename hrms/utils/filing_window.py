"""OT Request filing window — pure date logic, no Frappe imports.

HR's payroll rule (given 2026-08-19, replacing the calendar-month shape
"confirmed" on 2026-08-12 that turned out to be the wrong cutoff entirely —
it made the previous-month half of an OPEN cycle unfileable, which staff
correctly reported as "cannot backdate"):

  * The OT cutoff cycle runs the **16th of one month through the 15th of
    the next**. A claim's cycle decides which payroll pays it; anything
    filed after a cycle's 15th simply lands in the NEXT month's payroll.
    Payment timing is payroll's concern — filing is never refused for
    missing a cutoff.
  * Backdated OT is allowed for two months: filing is refused only when the
    OT date lies before the cycle start two cycles back. The fence is
    anchored to a cycle boundary (always a 16th), not rolled daily from
    "today", so it sits still for the whole cycle.

Example — today 2026-08-19: the current cycle began 16 Aug, so the earliest
filable OT date is 16 June. On 2026-01-10 the current cycle began
16 Dec 2025 and the earliest date is 16 Oct 2025.
"""

import logging
from datetime import date

logger = logging.getLogger(__name__)

#: The day a cutoff cycle begins — HR: "OT cutoff 16th (last month) to 15th
#: (current month)".
CYCLE_START_DAY = 16

#: HR: "allow backdated OT for 2 months" — measured in cycles, anchored to
#: their 16th boundaries.
BACKDATE_CYCLES = 2


def cycle_start(day: date) -> date:
	"""The 16th that began the cutoff cycle containing `day`."""
	if day.day >= CYCLE_START_DAY:
		return day.replace(day=CYCLE_START_DAY)
	year, month = (day.year, day.month - 1) if day.month > 1 else (day.year - 1, 12)
	logger.debug("[filing_window] %s belongs to the cycle started %s-%s-16", day, year, month)
	return date(year, month, CYCLE_START_DAY)


def earliest_filable_date(today: date) -> date:
	"""The oldest OT date still filable: the cycle start BACKDATE_CYCLES ago."""
	start = cycle_start(today)
	year, month = start.year, start.month - BACKDATE_CYCLES
	while month < 1:
		month += 12
		year -= 1
	earliest = date(year, month, CYCLE_START_DAY)
	logger.debug("[filing_window] earliest filable date on %s is %s", today, earliest)
	return earliest


def is_within_ot_filing_window(ot_date: date, today: date) -> bool:
	allowed = ot_date >= earliest_filable_date(today)
	logger.debug("[filing_window] ot_date=%s today=%s -> %s", ot_date, today, allowed)
	return allowed
