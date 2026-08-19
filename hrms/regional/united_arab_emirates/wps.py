# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import logging

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, getdate

from hrms.hr.utils import is_hr_operator

logger = logging.getLogger(__name__)


def build_sif_content(
	edr_rows: list[dict],
	employer_unique_id: str,
	payer_bank_code: str,
	creation_datetime,
	salary_month,
) -> str:
	"""Assemble a WPS SIF file (classic MOHRE agent format).

	EDR,<labour card 14>,<agent id 9>,<account>,<start ddmmyyyy>,
	    <end ddmmyyyy>,<days>,<fixed income>,<variable income>,<leave days>
	SCR,<employer id>,<payer bank code>,<creation ddmmyyyy>,<creation HHMM>,
	    <salary month MMYYYY>,<edr count>,<total salary>
	"""
	lines = []
	total = 0.0
	for row in edr_rows:
		total += flt(row["fixed_income"]) + flt(row["variable_income"])
		lines.append(
			",".join(
				[
					"EDR",
					row["labour_card_number"],
					row["agent_id"],
					row["account_number"],
					getdate(row["start_date"]).strftime("%d%m%Y"),
					getdate(row["end_date"]).strftime("%d%m%Y"),
					str(int(row["days"])),
					f"{flt(row['fixed_income']):.2f}",
					f"{flt(row['variable_income']):.2f}",
					str(int(row.get("leave_days") or 0)),
				]
			)
		)

	creation = get_datetime(creation_datetime)
	lines.append(
		",".join(
			[
				"SCR",
				employer_unique_id,
				payer_bank_code,
				creation.strftime("%d%m%Y"),
				creation.strftime("%H%M"),
				getdate(salary_month).strftime("%m%Y"),
				str(len(edr_rows)),
				f"{total:.2f}",
			]
		)
	)
	return "\n".join(lines)


@frappe.whitelist()
def get_wps_sif(payroll_entry: str, employer_unique_id: str, payer_bank_code: str) -> dict:
	"""WPS SIF file for a submitted Payroll Entry's salary slips.

	Net pay is reported as fixed income and variable income as 0 — split
	the fields once variable pay is modelled separately.
	"""
	_check_access()

	entry = frappe.get_doc("Payroll Entry", payroll_entry)
	slips = frappe.get_all(
		"Salary Slip",
		filters={"payroll_entry": payroll_entry, "docstatus": 1},
		fields=["name", "employee", "start_date", "end_date", "payment_days", "net_pay"],
	)
	if not slips:
		frappe.throw(_("No submitted salary slips found for Payroll Entry {0}.").format(payroll_entry))

	edr_rows = []
	missing = []
	for slip in slips:
		employee = frappe.db.get_value(
			"Employee",
			slip.employee,
			["labour_card_number", "wps_agent_id", "bank_ac_no", "employee_name"],
			as_dict=True,
		)
		absent = [
			label
			for field, label in (
				("labour_card_number", "Labour Card Number"),
				("wps_agent_id", "WPS Agent ID"),
				("bank_ac_no", "Bank Account No"),
			)
			if not employee.get(field)
		]
		if absent:
			missing.append(f"{slip.employee} ({employee.employee_name}): {', '.join(absent)}")
			continue
		edr_rows.append(
			{
				"labour_card_number": employee.labour_card_number,
				"agent_id": employee.wps_agent_id,
				"account_number": employee.bank_ac_no,
				"start_date": slip.start_date,
				"end_date": slip.end_date,
				"days": slip.payment_days,
				"fixed_income": slip.net_pay,
				"variable_income": 0,
				"leave_days": 0,
			}
		)

	if missing:
		frappe.throw(
			_("Cannot build the WPS file. Employees missing WPS details:<br>{0}").format("<br>".join(missing))
		)

	now = frappe.utils.now_datetime()
	content = build_sif_content(edr_rows, employer_unique_id, payer_bank_code, now, entry.start_date)
	logger.info("[wps] user=%s payroll_entry=%s slips=%d", frappe.session.user, payroll_entry, len(edr_rows))
	return {
		"file_name": f"{employer_unique_id}{now.strftime('%d%m%Y%H%M%S')}.SIF",
		"content": content,
	}


def _check_access():
	if is_hr_operator(frappe.session.user):
		return
	frappe.throw(_("You are not permitted to generate WPS files."), frappe.PermissionError)
