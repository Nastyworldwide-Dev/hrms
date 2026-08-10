# Copyright (c) 2026, Frappe Technologies Pte. Ltd. and contributors
# For license information, please see license.txt

import logging
from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.model.document import Document

logger = logging.getLogger(__name__)


def normalise_instance_url(raw: str | None) -> tuple[str, str | None]:
	"""Reduce an operator-entered address to a bare scheme+host origin.

	Returns `(normalised_url, error)`; `error` is None when the value is usable.
	Pure so it can be tested without a bench — `validate_url` is the thin wrapper
	that turns an error into a user-facing throw.

	This value serves two masters: it is the PWA's redirect target AND the base
	the shadow sync appends `/api/method/...` to. Anything beyond an origin
	corrupts the second use *silently*. A trailing `?` is the dangerous case —
	`https://host?` + `/api/method/x` parses as the host with the entire API path
	as its QUERY STRING, so every call lands on the site root and gets the login
	page back with a 200. No exception, just HTML where JSON was expected.
	"""
	raw = (raw or "").strip()
	# Order matters: drop empty query/fragment markers before slashes, so
	# "https://host/?" normalises the same as "https://host?/".
	url = raw.rstrip("?#").rstrip("/").rstrip("?#").rstrip("/")

	if not url.startswith(("http://", "https://")):
		return url, "URL must start with http:// or https://"

	parsed = urlparse(url)
	if not parsed.netloc:
		return url, "URL must include a host, e.g. https://example.frappe.cloud"
	if parsed.query or parsed.fragment:
		return url, f"URL must have no query string or #fragment — got {raw}"
	if parsed.path not in ("", "/"):
		return url, f"URL must be the site root, not a path — got {parsed.path}"

	return url, None


class HRMSERPInstance(Document):
	def validate(self):
		self.validate_url()
		self.validate_company_not_claimed_twice()

	def validate_url(self):
		raw = self.url
		url, error = normalise_instance_url(raw)
		if error:
			frappe.throw(_(error))
		if url != (raw or "").strip():
			logger.info("[erp_instance] normalised URL %r -> %r", raw, url)
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
