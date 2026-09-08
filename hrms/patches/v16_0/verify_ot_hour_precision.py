"""POST model sync: verify approved hour fields have the intended representation."""

import logging

import frappe
from frappe import _
from frappe.utils import cint

from hrms.utils.ot_precision import OT_HOUR_FIELDS, OT_HOUR_PRECISION

logger = logging.getLogger(__name__)


def execute():
	logger.info("[ot_precision] verifying stored and effective OT hour precision")
	for doctype, fields in OT_HOUR_FIELDS.items():
		frappe.clear_cache(doctype=doctype)
		meta = frappe.get_meta(doctype)
		for field in fields:
			physical = frappe.db.sql(
				"""SELECT numeric_precision, numeric_scale FROM information_schema.columns
				WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s""",
				("tab" + doctype, field),
			)
			if (
				not physical
				or tuple(physical[0]) != (21, OT_HOUR_PRECISION)
				or cint(meta.get_field(field).precision) != OT_HOUR_PRECISION
			):
				frappe.throw(
					_(
						"OT hour precision verification failed for {0}.{1}; expected decimal(21,9) and field precision 9."
					).format(doctype, field)
				)
