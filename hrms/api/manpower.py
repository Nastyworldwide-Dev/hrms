"""Manpower Request: the two reads the Nadi wizard starts from.

`can_request` decides whether Requests offers "Manpower" at all (the controller refuses a sender
with no team regardless); `get_questions` is the list HR keeps in Manpower Request Settings. Both
are read-only.
"""

import logging

import frappe

from hrms.hr.doctype.manpower_request.manpower_request import can_file_manpower_request
from hrms.utils.identity import get_employee

logger = logging.getLogger(__name__)


@frappe.whitelist(methods=["GET", "POST"])
def can_request() -> bool:
	"""May the caller send a manpower request? HR, or someone with an Active direct report."""
	allowed = can_file_manpower_request(get_employee())
	logger.debug("[manpower] can_request for %s: %s", frappe.session.user, allowed)
	return allowed


@frappe.whitelist(methods=["GET", "POST"])
def get_questions() -> list[dict]:
	"""The active questions in the order HR set, shaped for the wizard.

	Read with the settings' own permissions bypassed on purpose: the sender holds no right to
	open the Settings, only to answer what it asks. Nothing but the question fields leaves here.
	"""
	settings = frappe.get_cached_doc("Manpower Request Settings")
	rows = sorted((row for row in settings.questions if row.active), key=lambda row: row.idx)
	logger.debug("[manpower] %d active question(s)", len(rows))
	return [
		{
			"step": int(row.step.split(" ", 1)[0]),
			"question": row.question,
			"answer_type": row.answer_type,
			"choices": [line.strip() for line in (row.choices or "").splitlines() if line.strip()],
			"required": 1 if row.required else 0,
			"help": row.help,
		}
		for row in rows
	]
