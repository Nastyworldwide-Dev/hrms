# Copyright (c) 2026, Frappe Technologies Pte. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import time_diff_in_seconds


class HRMSSyncRun(Document):
	"""Audit record for one cross-instance mirror run.

	Written by `hrms.sync.runner`; never edited by hand, which is why every
	field is read_only. Its only job is to make a run's outcome — and the
	watermark the next run starts from — answerable after the fact.
	"""

	@property
	def duration(self) -> float | None:
		"""Seconds the run took, or None while it is still Running."""
		if not (self.started_at and self.finished_at):
			return None
		return time_diff_in_seconds(self.finished_at, self.started_at)

	def onload(self):
		duration = self.duration
		if duration is None:
			return
		frappe.logger("hrms").debug(
			"[sync] run %s: status=%s pulled=%s written=%s skipped=%s in %ss",
			self.name,
			self.status,
			self.rows_pulled,
			self.rows_written,
			self.rows_skipped,
			duration,
		)
