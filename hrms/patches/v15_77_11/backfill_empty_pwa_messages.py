"""Backfill PWA Notification rows that landed with an empty message.

Before v15.77.9, `notify_approver` / `_notify_employee` passed raw plain
text to PWA Notification.message (a Text Editor field). Frappe's HTML
sanitiser stripped the unwrapped text on save, leaving rows persisted
with an empty `message` column. The mobile feed rendered those rows as
near-invisible cards — only the avatar and "Load more" button visible.

This one-shot patch derives a non-empty message for those legacy rows so
the existing frontend bundle (which has no client-side fallback) can
display something useful immediately, without waiting for a frontend
rebuild. The derived label is keyed off reference_document_type and, for
Remote Checkin Request, the current request status.

Idempotent: rows already carrying a message are skipped. Subsequent
re-runs only touch newly-blank rows (there shouldn't be any after
v15.77.9 plugged the leak).
"""

from __future__ import annotations

import logging

import frappe

logger = logging.getLogger(__name__)


_STATUS_LABELS = {
	"Pending": "Remote check-in awaiting your decision.",
	"Approved": "Remote check-in approved.",
	"Rejected": "Remote check-in rejected.",
}


def _wrap(text: str) -> str:
	# Mirror _create_pwa_notification's HTML wrapping so the sanitiser
	# doesn't strip the backfill the next time the row is saved.
	return f"<p>{frappe.utils.escape_html(text)}</p>"


def execute() -> None:
	rows = frappe.db.sql(
		"""
		SELECT name, reference_document_type, reference_document_name
		FROM `tabPWA Notification`
		WHERE (message IS NULL OR TRIM(message) = '' OR message = '<p></p>')
		""",
		as_dict=True,
	)
	if not rows:
		logger.info("[patch.v15_77_11] no empty PWA Notification rows to backfill")
		return

	logger.info("[patch.v15_77_11] backfilling %d empty PWA Notification rows", len(rows))

	status_cache: dict[str, str] = {}

	def status_for(request_name: str) -> str:
		if request_name in status_cache:
			return status_cache[request_name]
		status = frappe.db.get_value("Remote Checkin Request", request_name, "status") or ""
		status_cache[request_name] = status
		return status

	updated = 0
	for row in rows:
		ref_type = row.get("reference_document_type") or ""
		ref_name = row.get("reference_document_name") or ""

		if ref_type == "Remote Checkin Request" and ref_name:
			status = status_for(ref_name)
			label = _STATUS_LABELS.get(status, "Remote check-in update.")
		elif ref_type:
			label = f"New {ref_type}"
		else:
			label = "New notification"

		frappe.db.set_value(
			"PWA Notification",
			row["name"],
			"message",
			_wrap(label),
			update_modified=False,
		)
		updated += 1

	frappe.db.commit()
	logger.info("[patch.v15_77_11] backfilled %d rows", updated)
