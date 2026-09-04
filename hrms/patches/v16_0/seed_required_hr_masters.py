"""Advisory check: warn if the HR link-masters an Employee import needs are empty.

THE FAILURE, from HR importing employees on the live hub:

    LinkValidationError: Could not find Employment Type: Full-time

An Employee row links to Employment Type, Gender and Salutation. On a site whose
masters are still empty, importing — or manually saving — an Employee throws
before the row can land.

This patch deliberately does NOT seed guessed values. During a total migration
the masters are HR-owned and populated from the SOURCE's real values; inventing a
stock list here (e.g. "Full-time" when the source says "Permanent") splits the
master — imports then create a second, disjoint set and headcount-by-type reporting
silently splits, with nothing reconciling the two. Empty is not broken; it means
"not yet populated from source".

So this only REPORTS which required masters are still empty, loudly (Error Log +
print), so HR populates them from the source before the Employee import — the
"populate masters from source" step in the cutover runbook. It creates nothing.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

#: masters an Employee row links to that are NOT carried by the sync mirror, so they
#: are empty until HR populates them from the source before importing employees.
_REQUIRED_MASTERS = ("Employment Type", "Gender", "Salutation")


def empty_required_masters() -> list:
	"""Which required masters have no rows yet. Pure read, no writes."""
	logger.info("[seed_required_hr_masters] checking required HR masters")
	empty = []
	for doctype in _REQUIRED_MASTERS:
		if frappe.db.table_exists(doctype) and not frappe.db.count(doctype):
			empty.append(doctype)
	return empty


def execute():
	logger.info("[seed_required_hr_masters] advisory patch run")
	empty = empty_required_masters()
	if not empty:
		print("[seed_required_hr_masters] required HR masters populated")
		return
	msg = (
		"These HR masters are empty and an Employee import will fail on them: "
		f"{', '.join(empty)}. Populate each from the SOURCE's real values (not guessed "
		"defaults) before importing employees — see the cutover runbook."
	)
	logger.warning("[seed_required_hr_masters] %s", msg)
	frappe.log_error(title="HR masters empty before employee import", message=msg)
	print(f"[seed_required_hr_masters] WARNING: {msg}")
