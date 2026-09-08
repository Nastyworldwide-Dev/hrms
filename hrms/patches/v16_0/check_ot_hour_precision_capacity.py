"""PRE model sync: prevent integer truncation when widening the hour scale."""

import logging

import frappe
from frappe import _

from hrms.utils.ot_precision import OT_HOUR_FIELDS

logger = logging.getLogger(__name__)


def execute():
	logger.info("[ot_precision] checking integer capacity before schema synchronization")
	for doctype, fields in OT_HOUR_FIELDS.items():
		if not frappe.db.table_exists(doctype):
			continue  # fresh installations have no stored values to preserve
		for field in fields:
			if not frappe.db.has_column(doctype, field):
				continue
			# Identifiers come only from the fixed field manifest above.
			count = frappe.db.sql(
				f"SELECT COUNT(*) FROM `tab{doctype}` WHERE ABS(`{field}`) >= %s", (10**12,)
			)[0][0]
			if count:
				logger.error(
					"[ot_precision] capacity preflight refused %s.%s (%s rows)", doctype, field, count
				)
				frappe.throw(
					_(
						"Cannot increase OT hour precision: {0}.{1} has {2} values outside the supported integer capacity. Review those values before migrating."
					).format(doctype, field, count)
				)
