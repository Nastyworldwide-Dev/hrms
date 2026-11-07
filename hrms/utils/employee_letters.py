"""Letters Issued on Employee (HR, 7 Nov 2026).

A child table (Employee Letter Issued) listing every letter HR has issued to a
person, each pointing at the signed copy on SharePoint. Built the way the Cost
Tag/Center Allocation table is: custom fields defined once here, used by the
install path (hrms.setup.get_custom_fields) and the rollout patch
(v16_0.add_employee_letters_issued).

WHO SEES IT
-----------
Both fields sit at permlevel 1, the level HR User, HR Manager and System Manager
already hold on Employee. hrms.utils.permlevel_guard re-asserts those rows on
every migrate, so no extra permission code lives here. Staff hold no level-1 row
and Frappe strips the table from any Employee they open.
"""

import logging
from urllib.parse import urlsplit

import frappe
from frappe import _
from frappe.utils import getdate

logger = logging.getLogger(__name__)

TABLE = "letters_issued"
SHAREPOINT_HOST = "sharepoint.com"

#: HR's list, in HR's order. Seeded on rollout; HR may add more in Desk.
LETTER_TYPES = (
	"Offer Letter",
	"Appointment Letter",
	"Probation Confirmation",
	"Probation Extension",
	"Contract Renewal",
	"Promotion",
	"Salary Adjustment",
	"Allowance",
	"Transfer",
	"Interim / Pemangku Appointment",
	"Warning Letter",
	"Show Cause",
	"Termination",
	"Resignation Acceptance",
	"Release / Experience Letter",
	"Other",
)


def get_letter_fields() -> dict:
	"""The one definition, used by the install path and the rollout patch."""
	return {
		"Employee": [
			{
				"collapsible": 1,
				"fieldname": "letters_issued_section",
				"fieldtype": "Section Break",
				"label": _("Letters Issued"),
				"insert_after": "interco_cost_allocation",
				"permlevel": 1,
			},
			{
				"fieldname": TABLE,
				"fieldtype": "Table",
				"label": _("Letters Issued"),
				"options": "Employee Letter Issued",
				"insert_after": "letters_issued_section",
				"permlevel": 1,
				"description": _(
					"Every letter issued to this person, newest first, with its SharePoint link."
				),
			},
		]
	}


def _is_sharepoint_link(link: str) -> bool:
	"""https:// and a host that is sharepoint.com or one of its subdomains.

	The host is checked, not the whole string: "contains sharepoint.com" would
	accept https://evil.com/sharepoint.com and https://sharepoint.com.evil.com.
	A login part (user@) or a backslash is refused outright."""
	if not link.lower().startswith("https://"):
		return False
	# Python and browsers parse these differently: urlsplit takes
	# https://evil.com\\@sharepoint.com as host sharepoint.com, a browser reads
	# "\\" as "/" and opens evil.com. Refuse anything they could disagree on.
	if any(ch == "\\" or ch.isspace() or ord(ch) < 32 for ch in link):
		return False
	parts = urlsplit(link)
	if "@" in parts.netloc:
		return False
	host = (parts.hostname or "").lower()
	return host == SHAREPOINT_HOST or host.endswith("." + SHAREPOINT_HOST)


def validate_letters(doc, method=None):
	"""Employee.validate: every link is a SharePoint https link; newest letter first."""
	rows = doc.get(TABLE) or []
	if not rows:
		return

	for row in rows:
		link = (row.sharepoint_link or "").strip()
		row.sharepoint_link = link
		if not _is_sharepoint_link(link):
			frappe.throw(
				_(
					"Letters Issued row {0}: the SharePoint Link must start with https:// and be on {1}."
				).format(row.idx, SHAREPOINT_HOST)
			)

	# stable, so two letters on one day keep the order HR entered them
	rows.sort(key=lambda r: getdate(r.date_issued), reverse=True)
	for idx, row in enumerate(rows, start=1):
		row.idx = idx
	doc.set(TABLE, rows)
	logger.info("[employee_letters] employee=%s letters=%d", doc.name, len(rows))


def seed_letter_types() -> list:
	"""Create any of HR's letter types that are missing. Idempotent."""
	added = []
	for letter_type in LETTER_TYPES:
		if frappe.db.exists("HR Letter Type", letter_type):
			continue
		frappe.get_doc({"doctype": "HR Letter Type", "letter_type": letter_type}).insert(
			ignore_permissions=True
		)
		added.append(letter_type)
	logger.info("[employee_letters] seeded %d letter types", len(added))
	return added
