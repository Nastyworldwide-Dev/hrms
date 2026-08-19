# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_first_day, get_last_day, getdate

from hrms.hr.utils import (
	validate_active_employee,
	validate_filing_for_self,
	validate_mandatory_attachment,
	validate_self_submission,
)
from hrms.utils.filing_window import earliest_filable_date, is_within_ot_filing_window
from hrms.utils.ot_calculation import get_day_ot_breakdown

logger = logging.getLogger(__name__)

OT_PAY = "Overtime Pay"
REPLACEMENT_LEAVE = "Replacement Leave"

# a replacement-leave claim buys leave in 4-hour half-day steps
HOURS_PER_HALF_DAY = 4


class OTRequest(Document):
	def validate(self):
		validate_active_employee(self.employee)
		validate_filing_for_self(self)
		self.validate_filing_window()
		self.set_compensation()
		self.set_punch_verified_cap()
		self.validate_claimed_hours()
		self.validate_duplicate_request()

	def validate_filing_window(self):
		# HR's cutoff rule (2026-08-19): cycles run the 16th through the 15th,
		# backdating reaches two cycles, and filing after a cycle's cutoff is
		# NOT refused — it just pays in the next payroll. Amendments re-file a
		# copy of an in-window original, so the window doesn't apply to them.
		if not self.is_new() or self.amended_from:
			return
		today = getdate()
		ot_date = getdate(self.ot_date)
		if ot_date > today:
			frappe.throw(_("OT Date cannot be in the future"))
		if not is_within_ot_filing_window(ot_date, today):
			logger.info("[ot_request] out-of-window filing rejected: %s for %s", self.employee, ot_date)
			frappe.throw(
				_(
					"OT for {0} can no longer be claimed — backdating reaches two payroll cycles; the earliest claimable date today is {1}."
				).format(frappe.bold(str(ot_date)), frappe.bold(str(earliest_filable_date(today))))
			)

	def set_compensation(self):
		# fixed by the employee's HR-managed flag; never a form choice
		eligible = frappe.db.get_value("Employee", self.employee, "eligible_for_overtime_pay")
		self.compensation = OT_PAY if cint(eligible) else REPLACEMENT_LEAVE

	def set_punch_verified_cap(self):
		breakdown = get_day_ot_breakdown(self.employee, self.ot_date)
		# whole hours only — minutes are not counted
		self.punch_ot_hours = int(flt(breakdown["ot_hours"]))
		if not self.shift:
			self.shift = frappe.db.get_value(
				"Attendance",
				{"employee": self.employee, "attendance_date": self.ot_date, "docstatus": ("<", 2)},
				"shift",
			)
		logger.info(
			"[ot_request] %s %s punch cap %sh (raw %.2f)",
			self.employee,
			self.ot_date,
			self.punch_ot_hours,
			flt(breakdown["ot_hours"]),
		)

	def validate_claimed_hours(self):
		if cint(self.claimed_hours) <= 0:
			frappe.throw(_("Claimed Hours must be at least 1"))
		if cint(self.claimed_hours) > cint(self.punch_ot_hours):
			frappe.throw(
				_(
					"Cannot claim {0} hours — your check-outs prove at most {1} hours of overtime for {2}."
				).format(
					frappe.bold(self.claimed_hours),
					frappe.bold(self.punch_ot_hours),
					frappe.bold(str(self.ot_date)),
				)
			)

	def validate_duplicate_request(self):
		duplicate = frappe.db.exists(
			"OT Request",
			{
				"employee": self.employee,
				"ot_date": self.ot_date,
				"docstatus": ("<", 2),
				"name": ("!=", self.name or "New OT Request"),
			},
		)
		if duplicate:
			frappe.throw(
				_("An OT Request for {0} already exists: {1}").format(
					frappe.bold(str(self.ot_date)), duplicate
				)
			)

	def on_submit(self):
		validate_self_submission(self)
		validate_mandatory_attachment(self)

	def on_cancel(self):
		# hours already converted by a Replacement Leave Claim can't be
		# cancelled out from under it
		if self.compensation != REPLACEMENT_LEAVE:
			return
		month_start = get_first_day(self.ot_date)
		# exclude self explicitly: by the time on_cancel runs, docstatus=2 is
		# already persisted so the sum would exclude it anyway — but the guard
		# must not depend on that ordering
		bank = get_replacement_leave_bank(self.employee, month_start, exclude_request=self.name)
		remaining_after_cancel = bank["hours_total"] - bank["hours_claimed"]
		logger.info(
			"[ot_request] cancel %s: bank %s, claimed %s, after-cancel %s",
			self.name,
			bank["hours_total"],
			bank["hours_claimed"],
			remaining_after_cancel,
		)
		if remaining_after_cancel < 0:
			frappe.throw(
				_(
					"Cannot cancel: {0} of this month's overtime hours were already converted to "
					"Replacement Leave. Cancel the Replacement Leave Claim first."
				).format(frappe.bold(bank["hours_claimed"]))
			)


def get_replacement_leave_bank(employee: str, month_start=None, exclude_request: str | None = None) -> dict:
	"""The month's convertible hours: approved replacement-leave OT hours minus
	hours consumed by claims filed against that month (drafts included, so a
	pending claim can't be double-funded)."""
	logger.info("[ot_request] bank query %s month=%s exclude=%s", employee, month_start, exclude_request)
	# CALENDAR month by decision (2026-08-19): only the FILING window follows
	# the 16th-to-15th payroll cycle (utils/filing_window.py). The bank month
	# and the OT cap keep the 1st-to-31st counting the older branches always
	# had — the cutoff was the only thing staff ever reported.
	month_start = get_first_day(month_start or getdate())
	month_end = get_last_day(month_start)

	ot_filters = {
		"employee": employee,
		"compensation": REPLACEMENT_LEAVE,
		"docstatus": 1,
		"ot_date": ("between", [month_start, month_end]),
	}
	if exclude_request:
		ot_filters["name"] = ("!=", exclude_request)
	# Frappe v16 refuses SQL functions passed as SELECT strings
	# ("sum(claimed_hours)"), so the totals are summed from the rows. One
	# employee-month is at most a handful of rows, so this stays cheap.
	hours_total = sum(
		flt(row.claimed_hours) for row in frappe.get_all("OT Request", ot_filters, ["claimed_hours"])
	)
	hours_claimed = sum(
		flt(row.hours_cost)
		for row in frappe.get_all(
			"Replacement Leave Claim",
			{
				"employee": employee,
				"docstatus": ("<", 2),
				"bank_month": month_start,
			},
			["hours_cost"],
		)
	)
	bank = {
		"month_start": month_start,
		"hours_total": cint(hours_total),
		"hours_claimed": cint(hours_claimed),
		"hours_available": cint(hours_total) - cint(hours_claimed),
	}
	logger.info("[ot_request] bank %s %s: %s", employee, month_start, bank)
	return bank
