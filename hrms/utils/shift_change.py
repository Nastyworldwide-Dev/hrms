"""HR changes a person's shift from a date, without touching a past day.

The rule, pure (no database): given what the person is rostered on and the day
the change starts, say which assignments to END the day before, which to REMOVE
(they start on or after the date, so nothing was worked on them yet), and what
to CREATE. hrms.api.roster.change_shift_from applies it.

Ending through `end_date` — editable after submit — is what avoids Frappe's
"linked to Employee Checkin" refusal on cancel: nothing is cancelled that has
punches. A worked day on or after the date is refused outright and the day is
named; HR moves worked days with Fix attendance.
"""

import logging
from collections import namedtuple
from datetime import timedelta

logger = logging.getLogger(__name__)

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

#: end: [(assignment, last day)], remove: [assignment], create: [(shift, weekdays or None)]
ShiftChangePlan = namedtuple("ShiftChangePlan", "start end remove create day_type")


class ShiftChangeRefused(Exception):
	"""The change would touch a worked day, or was not asked for properly."""


def plan_change(assignments, start, new_shifts, worked_days) -> ShiftChangePlan:
	"""What changing this person's shift from `start` does.

	`new_shifts`: [(shift_type, weekdays)] — weekdays None means every day; a
	weekday may belong to one shift only. `worked_days`: days that already carry
	punches or Attendance.
	"""
	if not new_shifts:
		raise ShiftChangeRefused("Pick the new shift.")
	if len(new_shifts) > 1 and any(not days for _shift, days in new_shifts):
		raise ShiftChangeRefused("With more than one shift, say which days each one covers.")
	seen = set()
	for _shift, days in new_shifts:
		for day in days or ():
			if day not in WEEKDAYS:
				raise ShiftChangeRefused(f"{day} is not a day of the week.")
			if day in seen:
				raise ShiftChangeRefused(f"{day} is on two shifts. Give each day one shift.")
			seen.add(day)

	worked = sorted(day for day in worked_days if day >= start)
	if worked:
		raise ShiftChangeRefused(
			f"{worked[0]} already has punches or attendance, so the shift cannot change from "
			f"{start}. Pick a later date, or fix that day in Fix attendance first."
		)

	end, remove, day_types = [], [], set()
	day_before = start - timedelta(days=1)
	for row in assignments:
		if row["end_date"] and row["end_date"] < start:
			continue  # finished before the change; the past stays as it was
		if row.get("synced_from_instance"):
			# owned by the old ERP (single-writer, hrms/sync/write_block.py): never edited here
			raise ShiftChangeRefused(
				f"{row['name']} comes from the old ERP, so it cannot be changed here. Change it there."
			)
		if row["start_date"] >= start:
			remove.append(row["name"])
		else:
			end.append((row["name"], day_before))
			if row.get("day_type") not in (None, "", "None"):
				day_types.add(row["day_type"])
	logger.info(
		"[shift_change] from %s: end %d, remove %d, create %d", start, len(end), len(remove), len(new_shifts)
	)
	# The Day Type carries over only from what is being ENDED, and only when those agree: a
	# removed future one-day override (an "Off Day" on 20 Oct) must never become the Day Type
	# of every new assignment (reviewer, 5 Oct 2026).
	day_type = day_types.pop() if len(day_types) == 1 else None
	return ShiftChangePlan(start, end, remove, list(new_shifts), day_type)

def preview_removed(assignments, start) -> list[dict]:
	"""What the change would REMOVE, for the dialog to say before HR presses it.

	Anything that starts on or after the date goes: a one-day Off Day override HR set on the
	roster, a later shift. Ended assignments and ones that merely run past the date (they are
	ended the day before, not removed) are not listed.
	"""
	return [
		{
			"name": row["name"],
			"shift_type": row["shift_type"],
			"start_date": row["start_date"],
			"end_date": row["end_date"],
			"day_type": row.get("day_type"),
		}
		for row in assignments
		if not (row["end_date"] and row["end_date"] < start) and row["start_date"] >= start
	]
