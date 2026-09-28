"""When may this person leave today? (owner, 28 Sep 2026)

The shift's end, pushed later by however late they came in. Early is not
credited: in before the start still leaves at the end. The same rule overtime
is paid by (ot_calculation._ot_window_begin), so Today's card and the pay can
never disagree about when the working day is done.

A half day off moves the day's start or end to the middle of the shift, as
late/early marking already does (half_day_session.late_early_bounds): AM off
starts the day at the midpoint, PM off ends it there.

Display only. It decides nothing about attendance, hours or pay.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def leave_by(first_in: datetime | None, shift_start, shift_end, session: str | None = None):
	"""The time the person may leave, or None when there is nothing to measure. Pure."""
	if not (first_in and shift_start and shift_end):
		return None
	from hrms.utils.half_day_session import late_early_bounds

	day_starts, day_ends = late_early_bounds(shift_start, shift_end, session)
	late = max(first_in - day_starts, timedelta(0))
	result = day_ends + late
	logger.debug(
		"[leave_by] in %s, day %s-%s (%s) -> leave by %s", first_in, day_starts, day_ends, session, result
	)
	return result
