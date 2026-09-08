# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The PWA's native Helpdesk front end (v16.23.0).

Thin, permission-respecting wrappers over the Frappe Helpdesk app so the HRMS
PWA can list, raise, read and reply to HD Tickets without leaving for the
Helpdesk portal. Visibility is Helpdesk's own: `frappe.get_list` runs its
`permission_query` (customers see raised_by / contact / customer rows, agents
see everything) and `get_one` re-checks read permission per ticket. The one
thing added here is identity — every row carries `raised_by_name`, the
Employee behind the raising user, because the HRM must show WHO raised it.

Every entry point degrades cleanly on a site without the Helpdesk app: the
PWA probes `is_available` first and hides the section.
"""

import logging

import frappe
from frappe import _

logger = logging.getLogger(__name__)

TICKET_FIELDS = [
	"name",
	"subject",
	"status",
	"priority",
	"ticket_type",
	"raised_by",
	"opening_date",
	"creation",
	"modified",
	"_assign",
]


@frappe.whitelist()
def is_available() -> bool:
	"""True when the Helpdesk app is installed on this site."""
	return "helpdesk" in frappe.get_installed_apps()


def _require_helpdesk():
	if not is_available():
		frappe.throw(_("Helpdesk is not installed on this site."), frappe.DoesNotExistError)


def _attach_raiser_names(rows: list[dict]) -> list[dict]:
	"""Stamp `raised_by_name` on each row: Employee name for the raising user,
	the raw email when no Employee matches, empty when raised_by is unset."""
	users = sorted({r.get("raised_by") for r in rows if r.get("raised_by")})
	names = {}
	if users:
		for emp in frappe.get_all(
			"Employee", filters={"user_id": ["in", users]}, fields=["user_id", "employee_name"]
		):
			names[emp["user_id"]] = emp["employee_name"]
	for row in rows:
		user = row.get("raised_by")
		row["raised_by_name"] = names.get(user, user) if user else ""
	logger.info("[helpdesk] raiser names resolved for %d row(s), %d employee(s)", len(rows), len(names))
	return rows


@frappe.whitelist()
def list_tickets(limit: int = 100) -> list[dict]:
	"""Tickets the caller may see, newest activity first, with who raised each."""
	_require_helpdesk()
	rows = frappe.get_list(
		"HD Ticket",
		fields=TICKET_FIELDS,
		order_by="modified desc",
		limit_page_length=int(limit or 100),
	)
	return _attach_raiser_names(rows)


@frappe.whitelist()
def get_ticket(name: str) -> dict:
	"""One ticket with its conversation, via Helpdesk's own portal read."""
	_require_helpdesk()
	from helpdesk.helpdesk.doctype.hd_ticket.api import get_one

	ticket = get_one(name, is_customer_portal=True)
	_attach_raiser_names([ticket])
	assigned = frappe.parse_json(ticket.get("_assign") or "[]") or []
	ticket["assigned_to_name"] = frappe.db.get_value("User", assigned[-1], "full_name") if assigned else ""
	logger.info("[helpdesk] ticket %s read by %s", name, frappe.session.user)
	return ticket


@frappe.whitelist()
def new_ticket(
	subject: str, description: str, ticket_type: str | None = None, priority: str | None = None
) -> dict:
	"""Raise a ticket as the session user (via_customer_portal, like the portal)."""
	subject = (subject or "").strip()
	description = (description or "").strip()
	if not subject or not description:
		frappe.throw(_("A subject and a description are required."))
	_require_helpdesk()
	from helpdesk.helpdesk.doctype.hd_ticket.api import new

	doc = {"subject": subject, "description": description}
	if ticket_type:
		doc["ticket_type"] = ticket_type
	if priority:
		doc["priority"] = priority
	ticket = new(doc)
	logger.info("[helpdesk] ticket %s raised by %s", ticket.name, frappe.session.user)
	return {"name": ticket.name}


@frappe.whitelist()
def reply(name: str, message: str) -> dict:
	"""Customer reply on a ticket; Helpdesk reopens a resolved ticket itself."""
	message = (message or "").strip()
	if not message:
		frappe.throw(_("Write a reply first."))
	_require_helpdesk()
	# "read", not "write": Helpdesk's own portal lets a customer reply on any
	# ticket they can read (create_communication_via_contact saves with
	# ignore_permissions). Read is what the customer permission_query scopes,
	# so this is the same fence the portal applies — tightening it to "write"
	# would refuse every employee reply.
	frappe.has_permission("HD Ticket", "read", name, throw=True)
	ticket = frappe.get_doc("HD Ticket", name)
	ticket.create_communication_via_contact(message)
	logger.info("[helpdesk] reply on %s by %s", name, frappe.session.user)
	return {"name": name, "status": frappe.db.get_value("HD Ticket", name, "status")}


@frappe.whitelist()
def get_options() -> dict:
	"""Ticket type and priority choices for the raise form."""
	_require_helpdesk()
	return {
		"types": frappe.get_all("HD Ticket Type", pluck="name", order_by="name asc"),
		"priorities": frappe.get_all("HD Ticket Priority", pluck="name", order_by="name asc"),
	}
