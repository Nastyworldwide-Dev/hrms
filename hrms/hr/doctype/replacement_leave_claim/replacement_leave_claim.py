# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_first_day, get_link_to_form, getdate

from hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry import create_additional_leave_ledger_entry
from hrms.hr.doctype.ot_request.ot_request import HOURS_PER_HALF_DAY, get_replacement_leave_bank
from hrms.hr.utils import (
	get_leave_period,
	validate_active_employee,
	validate_mandatory_attachment,
	validate_self_submission,
)

logger = logging.getLogger(__name__)

REPLACEMENT_LEAVE_TYPE = "Replacement Leave"


class ReplacementLeaveClaim(Document):
	def validate(self):
		validate_active_employee(self.employee)
		self.set_claim_basis()
		self.validate_claimed_days()

	def set_claim_basis(self):
		# claims always convert the CURRENT month's bank — the month is pinned
		# at first save so approval landing next month still converts the
		# right bank
		if self.is_new() or not self.bank_month:
			self.bank_month = get_first_day(getdate())
		self.leave_type = REPLACEMENT_LEAVE_TYPE
		bank = get_replacement_leave_bank(self.employee, self.bank_month)
		# exclude this claim's own draft cost when revalidating an existing row
		own_cost = 0
		if not self.is_new():
			own_cost = cint(frappe.db.get_value("Replacement Leave Claim", self.name, "hours_cost") or 0)
		self.available_hours = bank["hours_available"] + own_cost
		logger.info(
			"[rl_claim] %s basis: month %s, available %sh, claiming %s days (%sh)",
			self.name,
			self.bank_month,
			self.available_hours,
			self.claimed_days,
			self.hours_cost,
		)

	def validate_claimed_days(self):
		days = flt(self.claimed_days)
		if days <= 0:
			frappe.throw(_("Days Claimed must be at least 0.5"))
		if (days * 2) % 1 != 0:
			frappe.throw(_("Days Claimed must be in half-day steps (0.5, 1.0, 1.5 ...)"))
		self.hours_cost = cint(days * 2 * HOURS_PER_HALF_DAY)
		if self.hours_cost > cint(self.available_hours):
			frappe.throw(
				_(
					"Cannot claim {0} day(s) ({1} hours) — only {2} banked overtime hours are available for {3}."
				).format(
					frappe.bold(days),
					frappe.bold(self.hours_cost),
					frappe.bold(self.available_hours),
					frappe.bold(
						self.bank_month.strftime("%B %Y")
						if hasattr(self.bank_month, "strftime")
						else str(self.bank_month)
					),
				)
			)

	def on_submit(self):
		validate_self_submission(self)
		validate_mandatory_attachment(self)
		self.add_to_leave_allocation()

	def add_to_leave_allocation(self):
		"""Approval is the moment the days land in the allocation — mirrors
		CompensatoryLeaveRequest.on_submit (top-up or create, ledger entry)."""
		days = flt(self.claimed_days)
		valid_from = getdate()
		leave_period = get_leave_period(valid_from, valid_from, self.company)
		if not leave_period:
			frappe.throw(
				_("No active Leave Period covers {0} — create one before approving this claim.").format(
					frappe.bold(str(valid_from))
				)
			)

		allocation = self.get_existing_allocation(valid_from)
		if allocation:
			allocation.new_leaves_allocated += days
			allocation.validate()
			allocation.db_set("new_leaves_allocated", allocation.total_leaves_allocated)
			allocation.db_set("total_leaves_allocated", allocation.total_leaves_allocated)
			create_additional_leave_ledger_entry(allocation, days, valid_from)
		else:
			allocation = self.create_leave_allocation(leave_period, days, valid_from)

		self.db_set("leave_allocation", allocation.name)
		logger.info("[rl_claim] %s approved: +%s day(s) -> %s", self.name, days, allocation.name)
		frappe.msgprint(
			_("{0} day(s) added to Replacement Leave allocation {1}").format(
				frappe.bold(days), get_link_to_form("Leave Allocation", allocation.name)
			)
		)

	def on_cancel(self):
		if not self.leave_allocation:
			return
		days = flt(self.claimed_days)
		allocation = frappe.get_doc("Leave Allocation", self.leave_allocation)
		allocation.new_leaves_allocated -= days
		if allocation.new_leaves_allocated < 0:
			allocation.new_leaves_allocated = 0
		allocation.validate()
		allocation.db_set("new_leaves_allocated", allocation.total_leaves_allocated)
		allocation.db_set("total_leaves_allocated", allocation.total_leaves_allocated)
		create_additional_leave_ledger_entry(allocation, days * -1, getdate())
		logger.info("[rl_claim] %s cancelled: -%s day(s) from %s", self.name, days, allocation.name)

	def get_existing_allocation(self, valid_from):
		allocation = frappe.db.get_all(
			"Leave Allocation",
			filters={
				"employee": self.employee,
				"leave_type": self.leave_type,
				"from_date": ("<=", valid_from),
				"to_date": (">=", valid_from),
				"docstatus": 1,
			},
			limit=1,
		)
		if allocation:
			return frappe.get_doc("Leave Allocation", allocation[0].name)

	def create_leave_allocation(self, leave_period, days, valid_from):
		is_carry_forward = frappe.db.get_value("Leave Type", self.leave_type, "is_carry_forward")
		allocation = frappe.get_doc(
			dict(
				doctype="Leave Allocation",
				employee=self.employee,
				employee_name=self.employee_name,
				leave_type=self.leave_type,
				from_date=valid_from,
				to_date=leave_period[0].to_date,
				carry_forward=cint(is_carry_forward),
				new_leaves_allocated=days,
				total_leaves_allocated=days,
				description=self.explanation,
			)
		)
		allocation.insert(ignore_permissions=True)
		allocation.submit()
		return allocation
