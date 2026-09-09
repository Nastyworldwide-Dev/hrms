"""Which shift a punch belongs to, when an employee holds more than one.

10 September 2026: a person's old 7PM-3:30AM assignment was still Active after
HR moved them to a day shift. The IN at 09:35 went to the day shift; the OUT
at 19:45 went to the night shift, because the rule was "the shift whose START
is nearest the punch" — 19:00 is 45 minutes away, 10:00 is nine hours. Each
shift's job then saw one punch: Half Day, Absent under the night shift, no
overtime, an Off-Shift flag when neither window fitted. Every Half Day on a day
with a full IN and OUT had this shape.

One rule, pure, in the order a person would apply it:

1. An OUT belongs to the shift of the open IN it closes (same employee, within
   the session window, no OUT after it) — the shift does not change between a
   check-in and its check-out.
2. Otherwise the shift whose actual window (grace included) contains the punch;
   several → the one whose start is nearest.
3. Otherwise no shift: the punch is off-shift, named as such, never guessed onto
   the nearest start.

`superseded_assignments` is the companion rule: a new open-ended assignment
ends the employee's earlier open-ended ones the day before it starts, so the
old shift stops receiving punches and stops marking absences.
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

#: An OUT this long after its IN still closes that IN's shift (covers a night
#: shift plus overtime; a next-day punch further away is a new session).
SESSION_WINDOW = timedelta(hours=20)


def choose_shift(punch_time: datetime, log_type: str | None, candidates: list, open_in=None) -> dict | None:
	"""`candidates`: [{shift_type, actual_start, actual_end, ...}] for every active
	assignment, anchored on the punch date and the day before. `open_in`: the
	employee's latest unclosed IN as {shift, time}, or None. Returns the winning
	candidate, or None for off-shift."""
	if log_type == "OUT" and open_in and open_in.get("shift"):
		since_in = punch_time - open_in["time"]
		if timedelta(0) <= since_in <= SESSION_WINDOW:
			same = [c for c in candidates if _shift_name(c) == open_in["shift"]]
			if same:
				chosen = min(same, key=lambda c: abs((c["actual_start"] - open_in["time"]).total_seconds()))
				logger.info(
					"[shift_resolution] OUT %s closes the IN at %s on %s",
					punch_time,
					open_in["time"],
					open_in["shift"],
				)
				return chosen
	inside = [c for c in candidates if c["actual_start"] <= punch_time <= c["actual_end"]]
	if not inside:
		logger.info(
			"[shift_resolution] %s %s falls in no assigned shift window: off-shift", log_type, punch_time
		)
		return None
	# An IN is nearest its shift's start; an OUT nearest its shift's end. An OUT
	# at 19:45 inside both a day shift ending 19:00 and a night shift starting
	# 19:00 is the day shift's, whatever the starts say.
	edge = "end_datetime" if log_type == "OUT" else "start_datetime"
	chosen = min(inside, key=lambda c: abs((c[edge] - punch_time).total_seconds()))
	if len(inside) > 1:
		logger.info(
			"[shift_resolution] %s %s inside %d windows; nearest start %s",
			log_type,
			punch_time,
			len(inside),
			_shift_name(chosen),
		)
	return chosen


def _shift_name(candidate: dict) -> str:
	shift_type = candidate.get("shift_type")
	return shift_type.name if hasattr(shift_type, "name") else shift_type


def superseded_assignments(
	existing: list, new_start, new_shift_type: str, new_name: str | None = None
) -> list:
	"""Which of `existing` [{name, shift_type, start_date, end_date}] a new
	open-ended assignment ends, and on which date: the ones that started
	earlier and still run on the new start date. Same shift type or the new row
	itself are left alone. Returns [(name, end_date)]."""
	closes = []
	for row in existing:
		if row.get("name") == new_name or row.get("shift_type") == new_shift_type:
			continue
		if row["start_date"] >= new_start:
			continue
		if row.get("end_date") and row["end_date"] < new_start:
			continue
		closes.append((row["name"], new_start - timedelta(days=1)))
	if closes:
		logger.info(
			"[shift_resolution] new %s from %s supersedes %s",
			new_shift_type,
			new_start,
			[c[0] for c in closes],
		)
	return closes
