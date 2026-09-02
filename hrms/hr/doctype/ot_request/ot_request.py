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
from hrms.mixins.pwa_notifications import PWANotificationsMixin
from hrms.utils.filing_window import earliest_filable_date, is_within_ot_filing_window
from hrms.utils.ot_calculation import get_day_ot_breakdown

logger = logging.getLogger(__name__)

OT_PAY = "Overtime Pay"
REPLACEMENT_LEAVE = "Replacement Leave"

# a replacement-leave claim buys leave in 4-hour half-day steps
HOURS_PER_HALF_DAY = 4


class OTRequest(Document, PWANotificationsMixin):
	def after_insert(self):
		# Once, when the request is filed. NOT in validate: that runs on every
		# save, so the approver would be messaged again on each edit — the
		# fastest way to teach somebody to ignore notifications. Shift Request
		# notifies from after_insert for the same reason.
		#
		# Before this, OT Request notified nobody. Its three sibling request
		# types all raise a PWA Notification; OT had no approver field, so the
		# mixin raised KeyError on it and was never wired up. A draft sat in a
		# list until an HR user happened to scroll past.
		self.notify_approver()

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
		# the real fractional hours — int() here floored minutes away and capped
		# every claim below what was actually worked (7.75h -> claimable 7)
		self.punch_ot_hours = flt(breakdown["ot_hours"])
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
		if flt(self.claimed_hours) <= 0:
			frappe.throw(_("Claimed Hours must be greater than 0"))
		if flt(self.claimed_hours) > flt(self.punch_ot_hours):
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
		# Submitting IS the payout for this doctype, so it must not happen before
		# somebody decided. And a REJECTION still reaches docstatus 1 — rejecting
		# is a decision, not a cancellation — so the consequence below is guarded
		# on the decision itself. Without that, pressing Reject would bank the overtime hours it was refusing.
		# ShiftRequest.on_submit is the pattern.
		if self.status not in ("Approved", "Rejected"):
			frappe.throw(
				_("{0} must be Approved or Rejected before it can be submitted.").format(_(self.doctype))
			)

	def on_cancel(self):
		# hours already converted by a Replacement Leave Claim can't be
		# cancelled out from under it
		if self.compensation != REPLACEMENT_LEAVE:
			return
		# exclude self explicitly: by the time on_cancel runs, docstatus=2 is
		# already persisted so the sum would exclude it anyway — but the guard
		# must not depend on that ordering. Today's claiming window: an OT still
		# in it whose hours a claim reserved drives remaining negative; one that
		# has aged out of every claim's window is free to cancel (its leave, if
		# any, was already granted through the claim).
		bank = get_replacement_leave_bank(self.employee, getdate(), exclude_request=self.name)
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


def get_replacement_leave_bank(employee: str, as_of=None, exclude_request: str | None = None) -> dict:
	"""Convertible replacement-leave hours in the current CLAIMING WINDOW —
	approved replacement-leave OT worked within the window, minus hours reserved
	by claims filed within it (drafts included, so a pending claim can't be
	double-funded).

	WINDOW = the same 2-cycle backdate window an OT request is filable in
	(utils/filing_window, HR's 16th-to-15th cutoff). Replacement-leave OT is
	claimable for exactly as long as it is file-able, so a backdated OT approved
	after its calendar month is no longer stranded. This REVERSES the 2026-08-19
	calendar-month bank by decision (given 2026-XX): that shape silently stranded
	backdated replacement-leave OT — hours banked in a month you could no longer
	file a claim against. HR policy is one window for both filing and claiming.

	Ledger safety: any claim that consumed in-window OT has creation >= ot_date
	>= window_start, so it is itself inside the window — debits fully cover the
	credits they spent. hours_available can still read negative once a credit
	ages out while its debit has not (see on_cancel, which needs that signal);
	callers that DISPLAY it floor at 0.
	"""
	as_of = getdate(as_of or getdate())
	window_start = earliest_filable_date(as_of)
	logger.info(
		"[ot_request] bank query %s window=%s..%s exclude=%s", employee, window_start, as_of, exclude_request
	)

	ot_filters = {
		# A rejected request reaches docstatus 1 like any other decision, and this
		# query has no on_submit to guard it — so without this line, declining
		# overtime would still bank the hours and grant replacement leave. Money,
		# out of a button that says Reject.
		"status": ("!=", "Rejected"),
		"employee": employee,
		"compensation": REPLACEMENT_LEAVE,
		"docstatus": 1,
		"ot_date": ("between", [window_start, as_of]),
	}
	if exclude_request:
		ot_filters["name"] = ("!=", exclude_request)
	# Frappe v16 refuses SQL functions passed as SELECT strings
	# ("sum(claimed_hours)"), so the totals are summed from the rows. One
	# employee-window is at most a handful of rows, so this stays cheap.
	hours_total = sum(
		flt(row.claimed_hours) for row in frappe.get_all("OT Request", ot_filters, ["claimed_hours"])
	)
	# Debits: active claims FILED within the window. A claim filed before the
	# window can't have consumed in-window OT (its creation would precede the OT
	# date), so `creation >= window_start` captures every relevant consumer.
	hours_claimed = sum(
		flt(row.hours_cost)
		for row in frappe.get_all(
			"Replacement Leave Claim",
			{
				"employee": employee,
				"docstatus": ("<", 2),
				"creation": (">=", window_start),
			},
			["hours_cost"],
		)
	)
	bank = {
		"window_start": window_start,
		"window_end": as_of,
		"hours_total": cint(hours_total),
		"hours_claimed": cint(hours_claimed),
		"hours_available": cint(hours_total) - cint(hours_claimed),
	}
	logger.info("[ot_request] bank %s %s..%s: %s", employee, window_start, as_of, bank)
	return bank
