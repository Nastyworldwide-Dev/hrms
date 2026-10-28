# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import logging

import frappe
from frappe import _
from frappe.utils import flt, getdate

logger = logging.getLogger(__name__)

TOLERANCE = 0.005


def validate_interco_allocation(doc, method=None):
	"""Employee.validate hook: Cost Tag/Center allocation rows are grouped by
	Year/Month (stored as the 1st of the month). Each month must cover exactly
	100% with no cost tag twice. An empty table is allowed — the allocation
	report then shows the employee's full cost as unallocated.

	The tag is a Cost Center. Rows saved while it was a Territory keep that
	Territory and stay valid, so HR never has to re-enter an old split."""
	rows = doc.get("interco_cost_allocation") or []
	if not rows:
		return

	seen = set()
	totals = {}
	for row in rows:
		if not row.allocation_month:
			frappe.throw(_("Cost Tag/Center allocation row {0}: Year/Month is required.").format(row.idx))
		row.allocation_month = getdate(row.allocation_month).replace(day=1)
		if flt(row.percentage) <= 0:
			frappe.throw(
				_("Cost Tag/Center allocation row {0}: percentage must be greater than 0.").format(row.idx)
			)
		tag = row.get("cost_center") or row.get("territory")
		if not tag:
			frappe.throw(
				_("Cost Tag/Center allocation row {0}: Cost Tag/Center is required.").format(row.idx)
			)
		key = (row.allocation_month, tag)
		if key in seen:
			frappe.throw(
				_("Cost Tag/Center allocation: {0} appears more than once in {1}.").format(
					tag, row.allocation_month.strftime("%b %Y")
				)
			)
		seen.add(key)
		totals[row.allocation_month] = totals.get(row.allocation_month, 0.0) + flt(row.percentage)

	for month, total in totals.items():
		if abs(total - 100.0) > TOLERANCE:
			frappe.throw(
				_("Cost Tag/Center allocation for {0} must total 100%, currently {1}.").format(
					month.strftime("%b %Y"), frappe.format(total, "Percent")
				)
			)
	logger.info("[interco_allocation] employee=%s rows=%d months=%d", doc.name, len(rows), len(totals))
