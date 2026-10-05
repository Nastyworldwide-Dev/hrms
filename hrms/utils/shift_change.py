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
ShiftChangePlan = namedtuple("ShiftChangePlan", "start end remove create")


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

	end, remove = [], []
	day_before = start - timedelta(days=1)
	for row in assignments:
		if row["end_date"] and row["end_date"] < start:
			continue  # finished before the change; the past stays as it was
		if row["start_date"] >= start:
			remove.append(row["name"])
		else:
			end.append((row["name"], day_before))
	logger.info(
		"[shift_change] from %s: end %d, remove %d, create %d", start, len(end), len(remove), len(new_shifts)
	)
	return ShiftChangePlan(start, end, remove, list(new_shifts))
