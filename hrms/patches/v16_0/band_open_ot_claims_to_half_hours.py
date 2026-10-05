"""Cut every UNDECIDED Overtime Pay claim to the half hour (owner ruling, 5 Oct 2026).

HR pays overtime in half hours; a claim typed between the steps (1.37) was saved as typed. New and
edited claims are cut when they are saved (OTRequest.band_typed_claim). This patch cuts the ones filed
before that rule and still waiting for a decision: docstatus 0, Overtime Pay, not Rejected.

NOT touched: a decided claim (submitted: an approver read that figure, and it may already be priced),
Replacement Leave (raw hours convert to days), a claim already on a half-hour step. The change goes
straight to the column, with no save: no notification, no approval reset, `modified` left as it was.
Every change is logged with the old and the new figure. Idempotent: a second run finds nothing to cut.
"""

import logging

import frappe
from frappe.utils import flt

from hrms.utils.ot_precision import half_hour_claim

logger = logging.getLogger(__name__)


def execute():
	if not frappe.db.exists("DocType", "OT Request"):
		return
	rows = frappe.get_all(
		"OT Request",
		filters={"docstatus": 0, "compensation": "Overtime Pay", "status": ("!=", "Rejected")},
		fields=["name", "claimed_hours"],
	)
	cut = 0
	for row in rows:
		typed = flt(row.claimed_hours)
		banded = half_hour_claim(typed)
		if banded == typed or banded <= 0:
			# on a step already, or under half an hour: left for its owner to correct (refusing here
			# would make a claim vanish; a zero claim would be refused on its next save anyway)
			if banded <= 0 < typed:
				logger.warning("[patch] %s claim %s is under half an hour: left as it is", row.name, typed)
			continue
		frappe.db.set_value("OT Request", row.name, "claimed_hours", banded, update_modified=False)
		logger.info("[patch] %s claimed_hours %s -> %s (half hours)", row.name, typed, banded)
		cut += 1
	logger.info("[patch] open Overtime Pay claims cut to the half hour: %d of %d", cut, len(rows))
