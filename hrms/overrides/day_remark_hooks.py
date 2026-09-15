"""doc_events that re-mark a past employee-day when its evidence changes.

Every handler ends in the one shared hrms.utils.day_remark.remark_day_after_commit
(one deduplicated engine re-mark per employee-day, after commit, protections
intact). The punch decision is wired in remote_checkin_request_hooks.

None of these handlers raises: a refresh that cannot be queued must never undo
the save it follows. Writes made with frappe.db.set_value (the engine's own
linking and skip-stamping) fire no doc_events, so the re-mark job cannot loop.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from frappe.utils import getdate

from hrms.utils.day_remark import remark_day_after_commit

logger = logging.getLogger(__name__)

#: What a punch edit must change to count as new evidence for its day.
EVIDENCE_FIELDS = (
	"time",
	"log_type",
	"shift",
	"shift_start",
	"skip_auto_attendance",
	"remote_approval_status",
)
#: A request longer than this re-marks only its first days; the nightly recovery reads the rest.
MAX_REQUEST_DAYS = 62


def _queue(employee, day, reason) -> None:
	try:
		remark_day_after_commit(employee, day, reason)
	except Exception:
		logger.exception(
			"[day_remark_hooks] could not queue the re-mark of %s on %s (%s)", employee, day, reason
		)


def _shift_day(row):
	value = row.get("shift_start") or row.get("time")
	return getdate(value) if value else None


def remark_punch_day(doc, method=None):
	"""Employee Checkin after_insert / on_trash: a punch added to or removed from a day."""
	if doc.get("synced_from_instance"):
		logger.debug("[day_remark_hooks] %s is mirrored: its source instance marks the day", doc.name)
		return
	_queue(doc.employee, _shift_day(doc), f"{doc.name} {method or 'changed'}")


def remark_changed_punch_day(doc, method=None):
	"""Employee Checkin on_update: skip ticked or cleared, time, type or shift edited.
	A punch moved to another day changes both days."""
	before = doc.get_doc_before_save()
	if before is None or doc.get("synced_from_instance"):
		return
	changed = [f for f in EVIDENCE_FIELDS if before.get(f) != doc.get(f)]
	if not changed:
		return
	logger.info("[day_remark_hooks] %s changed %s", doc.name, changed)
	for day in sorted({d for d in (_shift_day(before), _shift_day(doc)) if d}):
		_queue(doc.employee, day, f"{doc.name} edited ({', '.join(changed)})")


def remark_request_days(doc, method=None):
	"""Leave Application / Attendance Request on_cancel: the days it held go back to
	their punches. Approval needs nothing: the request's own row owns those days."""
	start, end = getdate(doc.from_date), getdate(doc.to_date)
	days = min((end - start).days + 1, MAX_REQUEST_DAYS)
	logger.info("[day_remark_hooks] %s %s cancelled: re-marking %d day(s)", doc.doctype, doc.name, days)
	for offset in range(days):
		_queue(doc.employee, start + timedelta(days=offset), f"{doc.doctype} {doc.name} cancelled")
