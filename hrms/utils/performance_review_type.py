"""Performance Review Type: what kind of review an Appraisal is (owner, 13 Nov 2026).

HR keep the list in Desk (Performance Review Type): add, rename, switch off. It
starts with the five HR named; seeding only adds the missing ones, so a type HR
renamed or switched off is never put back.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

STARTING_TYPES = (
	"Confirmation Review",
	"PIP Review",
	"Performance Review",
	"Assignment Review",
	"Others",
)


def seed_review_types() -> list:
	"""Create any of the starting review types that are missing. Idempotent."""
	added = []
	for review_type in STARTING_TYPES:
		if frappe.db.exists("Performance Review Type", review_type):
			continue
		frappe.get_doc({"doctype": "Performance Review Type", "review_type": review_type}).insert(
			ignore_permissions=True
		)
		added.append(review_type)
	logger.info("[performance_review_type] seeded %d review types", len(added))
	return added


#: Appraisal Cycle's Cycle Type -> its length in months (owner, 13 Nov 2026).
CYCLE_MONTHS = {"Monthly": 1, "Quarterly": 3, "Half Yearly": 6, "Yearly": 12}


def cycle_end(start, cycle_type):
	"""The last day of a cycle of this type that starts on `start`. Pure. None
	for a blank or unknown type: the end date is then whatever HR typed."""
	import datetime

	from dateutil.relativedelta import relativedelta

	months = CYCLE_MONTHS.get(cycle_type)
	if not (months and start):
		return None
	if isinstance(start, str):
		start = datetime.date.fromisoformat(start)
	return start + relativedelta(months=months) - datetime.timedelta(days=1)
