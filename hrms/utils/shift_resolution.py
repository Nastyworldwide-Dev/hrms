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
   check-in and its check-out. A punch continuing an open session, or
   returning from a break inside the closed session's scheduled hours
   (returns_from_break), keeps that session's shift too.
2. Otherwise the shift whose actual window (grace included) contains the punch;
   several → the shift the person is ROSTERED on (rostered_shift): the one whose
   scheduled hours hold the punch, else the day shift over a night one, else the
   earliest start of the day; nearest start/end only as the last tie-break. A
   tap never jumps to another shift because a buffer window overlaps (S2,
   15 Sep 2026: Ria's 18:33 IN sat in the day's 360-minute after-buffer and the
   night's 60-minute before-buffer; "nearest start" opened an invented night).
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
#: A punch this soon after the OUT that closed a session, inside that shift's
#: scheduled hours, is the return from a break (Group 1 review W1).
BREAK_RETURN_WINDOW = timedelta(hours=6)


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
	chosen = rostered_shift(punch_time, log_type, inside)
	if len(inside) > 1:
		logger.info(
			"[shift_resolution] %s %s inside %d windows; rostered shift %s",
			log_type,
			punch_time,
			len(inside),
			_shift_name(chosen),
		)
	return chosen


def crosses_midnight(candidate: dict) -> bool:
	"""A night shift for this rule: its scheduled end falls on a later date."""
	return candidate["end_datetime"].date() > candidate["start_datetime"].date()


def rostered_shift(punch_time: datetime, log_type: str | None, inside: list) -> dict:
	"""Which of the windows containing the punch (`inside`, non-empty) is the
	shift the person is rostered on — session first, rostered shift second
	(Nabil, 15 Sep 2026). In order, keeping the survivors of each step:

	1. the windows whose SCHEDULED hours (start..end, no grace) hold the punch;
	2. the day shifts (not crossing midnight) over the night ones, when both
	   remain — a day worker holding a stray night assignment is rostered on the
	   day, and a real double shift's night taps fall under step 1;
	3. the earliest scheduled start of the day (clock time, so a night anchored
	   on the day before does not win by starting "yesterday");
	4. the nearest edge — start for an IN, end for an OUT — for what is left,
	   e.g. the same shift anchored on two dates.

	log_type plays no part in 1-3: under "Alternating entries" the engine pairs
	by order, so the label must not move a tap to another shift."""
	pool = [c for c in inside if c["start_datetime"] <= punch_time <= c["end_datetime"]] or inside
	day_shifts = [c for c in pool if not crosses_midnight(c)]
	if day_shifts and len(day_shifts) < len(pool):
		pool = day_shifts
	earliest = min(c["start_datetime"].time() for c in pool)
	pool = [c for c in pool if c["start_datetime"].time() == earliest]
	edge = "end_datetime" if log_type == "OUT" else "start_datetime"
	chosen = min(pool, key=lambda c: abs((c[edge] - punch_time).total_seconds()))
	if len(inside) > 1:
		logger.info(
			"[shift_resolution] %s %s: rostered on %s (scheduled=%s, day=%s, earliest=%s) of %s",
			log_type,
			punch_time,
			_shift_name(chosen),
			any(c["start_datetime"] <= punch_time <= c["end_datetime"] for c in inside),
			bool(day_shifts),
			earliest,
			sorted({_shift_name(c) for c in inside}),
		)
	return chosen


def counts_toward_session(row) -> bool:
	"""A skip-stamped punch (a rejected one is skip-stamped) is not paired."""
	return not int(row.get("skip_auto_attendance") or 0) and row.get("remote_approval_status") != "Rejected"


# Whether the session is still open after the `group_count`-th counted punch of
# a shift group (same shift and shift_start). "Alternating entries" pairs a
# group's punches in order, so an even count has just closed a pair. A punch
# labelled OUT never leaves a session open either: an 18:31 OUT filed alone on a
# stray night shift closed the day, it did not start a night (Group 1 review
# C1, 14 Sep 2026).
def session_is_open(group_count, log_type) -> bool:
	return bool(group_count) and group_count % 2 == 1 and log_type != "OUT"


def _within_session(punch_time: datetime, stamp, since: datetime) -> bool:
	start, end = stamp.get("shift_actual_start"), stamp.get("shift_actual_end")
	if not start or not end:
		return False
	return timedelta(0) <= punch_time - since <= SESSION_WINDOW and start <= punch_time <= end


def continues_session(punch_time: datetime, earlier) -> bool:
	"""Whether a punch continues the session of `earlier` — the employee's
	stored punch just before it, as {time, log_type, group_count, shift,
	shift_actual_start, shift_actual_end}. True when the earlier punch has a
	shift, left its session OPEN (session_is_open), the gap is inside
	SESSION_WINDOW, and the earlier shift's actual window (grace included)
	contains the punch. The new punch's own log_type plays no part: under
	"Alternating entries" the engine pairs first and last of the shift group, so
	an 18:31 tap recorded as IN after an 08:55 IN is the day's end, not a night
	start (E4, 14 Sep 2026). A closed session is never continued — a day OUT at
	18:00 must not swallow the real night IN at 19:30 (C1)."""
	if not earlier or not earlier.get("shift"):
		return False
	if not session_is_open(earlier.get("group_count") or 0, earlier.get("log_type")):
		logger.info(
			"[shift_resolution] %s does not continue %s on %s: that session is closed (count=%s, %s)",
			punch_time,
			earlier.get("time"),
			earlier["shift"],
			earlier.get("group_count"),
			earlier.get("log_type"),
		)
		return False
	inside = _within_session(punch_time, earlier, earlier["time"])
	if inside:
		logger.info(
			"[shift_resolution] %s continues the session of %s on %s",
			punch_time,
			earlier["time"],
			earlier["shift"],
		)
	return inside


def returns_from_break(punch_time: datetime, log_type: str | None, earlier) -> bool:
	"""Whether a punch is the return from a break of the session `earlier`
	closed (Group 1 review W1, 14 Sep 2026): 08:55 IN, 13:00 OUT, 14:16 IN on a
	day worker holding a stray 19:30 night assignment. The 13:00 OUT closed the
	session, so continues_session declines, and nearest start then filed 14:16
	on Night (5h14 from 19:30, 5h16 from 09:00); the 18:00 OUT followed it and
	the afternoon and its overtime were lost.

	True when the punch is not an OUT, `earlier` (as in continues_session, with
	shift_start and shift_end) closed a real session of at least two punches,
	the punch lies inside that shift's SCHEDULED hours (no grace: a double
	shift's 19:30 night IN after an 18:00 day OUT stays on the night) and within
	BREAK_RETURN_WINDOW of the closing punch."""
	if log_type == "OUT" or not earlier or not earlier.get("shift"):
		return False
	count = earlier.get("group_count") or 0
	if count < 2 or session_is_open(count, earlier.get("log_type")):
		return False
	start, end = earlier.get("shift_start"), earlier.get("shift_end")
	if not start or not end:
		return False
	back = start <= punch_time <= end and timedelta(0) <= punch_time - earlier["time"] <= BREAK_RETURN_WINDOW
	logger.info(
		"[shift_resolution] %s after %s closed %s (%s-%s): return from break=%s",
		punch_time,
		earlier["time"],
		earlier["shift"],
		start,
		end,
		back,
	)
	return back


def session_restamps(anchor, later: list) -> list:
	"""Names of `later` punches (time ascending, after `anchor`) that belong to
	the anchor's session but carry another shift stamp. `anchor` carries
	group_count (its position in its shift group) and log_type.

	Punches already on the anchor's shift count toward the group and carry the
	walk forward. Another shift's punch joins only while the session is still
	open (session_is_open): the punch that closes it is restamped, nothing
	after it. Rejected and skip-stamped punches are neither counted nor moved.
	The walk stops where the session window ends, and at a punch that may not be
	rewritten — linked to an Attendance row (the engine or HR already settled
	it) or mirrored from another instance — since nothing after it can join the
	anchor's shift either."""
	key = (anchor.get("shift"), anchor.get("shift_start"))
	count = anchor.get("group_count") or 0
	previous = anchor
	names = []
	for row in later:
		if not counts_toward_session(row):
			continue
		if not _within_session(row["time"], anchor, previous["time"]):
			break
		if (row.get("shift"), row.get("shift_start")) == key:
			count += 1
			previous = row
			continue
		if not session_is_open(count, previous.get("log_type")):
			logger.info("[shift_resolution] session of %s closed before %s: walk stops", key, row["time"])
			break
		if row.get("attendance") or row.get("synced_from_instance"):
			logger.info(
				"[shift_resolution] %s at %s is on %s but locked (attendance=%s mirrored=%s): walk stops",
				row.get("name"),
				row["time"],
				row.get("shift"),
				row.get("attendance"),
				bool(row.get("synced_from_instance")),
			)
			break
		names.append(row["name"])
		previous = row
	return names


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
