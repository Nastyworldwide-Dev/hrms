"""HR Day Fix Log — one row per change to an employee-day, before and after.

SHARED, on purpose. `hrms.api.attendance_fix_day` (HR's Fix Day screen) writes
`source = "hr_fix_day"`; the automatic ERP backfill and the recovery write their
own entries with their own `source` and, for a batch, a `run` they can all be
undone by. `action` is free text and `before_state` / `after_state` are free
JSON, so a second writer needs no schema change and no second log.

Never written by a person: every field is read-only and every insert runs with
`ignore_permissions`. Two jobs:

* the trail — who changed which tap on whose day, why, and what the day said
  before and after the engine re-marked it;
* the undo — `before_state` holds each touched tap exactly as it stood, so
  `attendance_fix_day.undo_fix` can put it back and rebuild again.

Append-only by construction: an undone entry keeps its own row and is marked
`undone`, and the undo writes its own entry pointing back through `undo_of`.
"""

from frappe.model.document import Document


class HRDayFixLog(Document):
	pass
