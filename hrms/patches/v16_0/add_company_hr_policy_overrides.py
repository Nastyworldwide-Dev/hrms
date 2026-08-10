"""Create the per-company HR / Payroll policy override fields on Company.

Several HR policies lived in a single global singleton (HR Settings / Payroll
Settings), so one company's policy silently applied to every company on the
site — wrong once the site hosts entities in Malaysia, the UAE and China.
`hrms.utils.company_settings` resolves company override first, global second;
this patch creates the columns the override layer reads on existing sites.

Fresh installs do NOT rely on this patch (install_app marks patches as run
without executing them) — the same field list is part of
`hrms.setup.get_custom_fields()["Company"]`, which `after_install` creates.

Purely additive and idempotent: every field is created blank, so every company
keeps inheriting the global value and behaviour is unchanged until HR sets an
override deliberately.
"""

import logging

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.setup import get_company_hr_policy_fields

logger = logging.getLogger(__name__)


def execute():
	fields = get_company_hr_policy_fields()
	create_custom_fields({"Company": fields}, ignore_validate=True)
	logger.info("[patch] add_company_hr_policy_overrides created/verified %d Company fields", len(fields))
	frappe.db.commit()
