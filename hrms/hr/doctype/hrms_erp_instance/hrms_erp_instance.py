# Copyright (c) 2026, Frappe Technologies Pte. Ltd. and contributors
# For license information, please see license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document

logger = logging.getLogger(__name__)


class HRMSERPInstance(Document):
	def validate(self):
		self.validate_url()
		self.validate_company_not_claimed_twice()

	def validate_url(self):
		"""Staff are sent here from the PWA, so only absolute http(s) URLs are usable."""
		url = (self.url or "").strip().rstrip("/")
		if not url.startswith(("http://", "https://")):
			frappe.throw(_("URL must start with http:// or https://"))
		self.url = url

	def validate_company_not_claimed_twice(self):
		"""A company resolves to exactly one instance, so overlap would make the
		staff redirect ambiguous."""
		seen = set()
		for row in self.companies or []:
			if row.company in seen:
				frappe.throw(_("Company {0} is listed twice.").format(frappe.bold(row.company)))
			seen.add(row.company)

		if not seen:
			return

		clash = frappe.get_all(
			"HRMS ERP Instance Company",
			filters={"company": ("in", list(seen)), "parent": ("!=", self.name)},
			fields=["parent", "company"],
			limit=1,
		)
		if clash:
			logger.warning(
				"[erp_instance] %s claims company %s already held by %s",
				self.name,
				clash[0].company,
				clash[0].parent,
			)
			frappe.throw(
				_("Company {0} is already served by instance {1}.").format(
					frappe.bold(clash[0].company), frappe.bold(clash[0].parent)
				)
			)
