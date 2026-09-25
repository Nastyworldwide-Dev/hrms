"""The hours an approved Attendance Request carries, onto a row that exists.

"Fix a day" printed "Proposed hours were not applied" and dropped the times
whenever the day already had an Attendance row (owner, 25 Sep 2026). The
approver approved those times; they belong on the row. A day money already
paid is the one refusal, in words.
"""

import logging

logger = logging.getLogger(__name__)


def hours_for_existing_row(in_dt, out_dt, status, paid_by):
	"""(values to write, refusal sentence or None). Pure."""
	if not (in_dt and out_dt) or status == "Half Day":
		# a half day keeps no full-day span: it would contradict the status
		# and inflate overtime (the same rule a new row follows)
		return {}, None
	if paid_by:
		logger.info("[request_hours] typed hours refused: day already paid by %s", paid_by)
		return {}, f"The times were not applied: this day is already paid ({paid_by}). Ask HR to correct it."
	hours = round((out_dt - in_dt).total_seconds() / 3600, 2)
	return {"in_time": in_dt, "out_time": out_dt, "working_hours": hours}, None
