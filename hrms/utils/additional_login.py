"""A second login for one Employee (owner, 2 Nov 2026).

Aida had two Users — aida@nastyworldwide.com (her record's user_id) and
aida@qgdsz.com (the one she signs in with). Nadi resolves a login to an
Employee through user_id, so the second login reached nothing and every
section of Today failed. HR can now name that second login on the Employee;
`hrms.utils.identity` resolves either login to the same record, each on its
own, and the Employee role keeper (`employee_master`) keeps the role on both.

Guard rails, because this field IS authority over a person's HR data:
  * permlevel 1 — HR edits it; Employee Self Service cannot set its own;
  * unique — no other Employee may hold the address as user_id or as its own
    additional login (the resolver would deny both as AMBIGUOUS anyway; this
    refuses it at save so HR sees why);
  * not mirrored — `hrms.sync.runner.LOCALLY_OWNED_FIELDS`, like user_id.
"""

import logging

import frappe
from frappe import _
from frappe.query_builder.functions import Lower, Trim

logger = logging.getLogger(__name__)

FIELD = "additional_login_email"


def get_additional_login_fields() -> dict:
	"""The one definition, used by the install path and the rollout patch."""
	return {
		"Employee": [
			{
				"fieldname": FIELD,
				"fieldtype": "Data",
				"options": "Email",
				"label": _("Additional Login Email"),
				"insert_after": "user_id",
				# HR only: a self-set second login would let anyone claim any address
				"permlevel": 1,
				"description": _(
					"A second sign-in for this same person. Either email opens Nadi with this "
					"record's data. Must belong to no other employee."
				),
			}
		]
	}


def validate_additional_login(doc, method=None):
	"""Employee.validate: normalize the second login and refuse a clash."""
	from hrms.utils.identity import normalize_login

	value = normalize_login(doc.get(FIELD))
	if not value:
		doc.set(FIELD, None)
		return
	doc.set(FIELD, value)

	if value == normalize_login(doc.get("user_id")):
		frappe.throw(
			_("Additional Login Email is already this employee's User ID. Leave it empty."),
			title=_("Additional Login Email"),
		)

	employee = frappe.qb.DocType("Employee")
	clash = (
		frappe.qb.from_(employee)
		.select(employee.name)
		.where(
			(employee.name != (doc.name or ""))
			& ((Lower(Trim(employee.user_id)) == value) | (Lower(Trim(employee[FIELD])) == value))
		)
		.limit(1)
		.run(pluck=True)
	)
	if clash:
		logger.warning("[additional_login] %s refused on %s: already used by %s", value, doc.name, clash[0])
		frappe.throw(
			_("{0} is already the login of another employee ({1}). One login belongs to one person.").format(
				frappe.bold(value), clash[0]
			),
			title=_("Additional Login Email"),
		)
	logger.info("[additional_login] %s set as the additional login of %s", value, doc.name)
