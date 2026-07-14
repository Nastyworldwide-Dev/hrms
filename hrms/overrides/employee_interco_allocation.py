# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import logging

import frappe
from frappe import _
from frappe.utils import flt

logger = logging.getLogger(__name__)

TOLERANCE = 0.005


def validate_interco_allocation(doc, method=None):
	"""Employee.validate hook: interco allocation rows must cover exactly
	100% with no duplicate intercos. An empty table is allowed — the
	allocation report then falls back to the employee's Cost Tag at 100%."""
	rows = doc.get("interco_cost_allocation") or []
	if not rows:
		return

	seen = set()
	total = 0.0
	for row in rows:
		if flt(row.percentage) <= 0:
			frappe.throw(_("Interco allocation row {0}: percentage must be greater than 0.").format(row.idx))
		if row.territory in seen:
			frappe.throw(_("Interco allocation: {0} appears more than once.").format(row.territory))
		seen.add(row.territory)
		total += flt(row.percentage)

	if abs(total - 100.0) > TOLERANCE:
		frappe.throw(
			_("Interco allocation percentages must total 100%, currently {0}%.").format(
				frappe.format(total, "Percent")
			)
		)
	logger.info("[interco_allocation] employee=%s rows=%d total=%s", doc.name, len(rows), total)
