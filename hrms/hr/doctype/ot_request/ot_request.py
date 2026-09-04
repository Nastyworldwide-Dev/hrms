# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate

from hrms.hr.utils import (
	grant_replacement_leave,
	reverse_replacement_leave,
	validate_active_employee,
	validate_filing_for_self,
	validate_mandatory_attachment,
	validate_self_submission,
)
from hrms.mixins.pwa_notifications import PWANotificationsMixin
from hrms.utils.filing_window import earliest_filable_date, is_within_ot_filing_window
from hrms.utils.ot_calculation import (
	get_day_ot_breakdown,
	replacement_leave_days,
	round_ot_pay_hours,
)

logger = logging.getLogger(__name__)

OT_PAY = "Overtime Pay"
REPLACEMENT_LEAVE = "Replacement Leave"


def replacement_leave_hours_per_day() -> float:
	"""Banked overtime hours that convert to ONE day of replacement leave.

	HR-configurable via HR Settings; defaults to 8 (a standard working day) so a
	site that has not set it behaves exactly as the old hardcoded ratio (8h = 1
	day, 4h = half a day). Un-hardcoded because the 8 was baked into the backend
	AND copied into the PWA text — two places to drift, neither editable by HR.

	Fails open to 8: get_single_value RAISES on a site where the custom field is
	not present yet (before this release's patch runs, or a half-migrated site), and
	a replacement-leave claim must not crash on that. Same fail-open-to-default shape
	as _company_weekend in ot_calculation.
	"""
	try:
		value = frappe.db.get_single_value("HR Settings", "replacement_leave_hours_per_day")
	except Exception:
		logger.warning("[ot_request] replacement_leave_hours_per_day field missing — defaulting to 8")
		value = None
	return flt(value) or 8.0


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
		raw = flt(breakdown["ot_hours"])
		# OT Pay is billed in HR's 30-minute bands (round_ot_pay_hours); Replacement
		# Leave keeps the raw fractional hours and converts them to days downstream.
		# set_compensation runs before this in validate(), so self.compensation is set.
		self.punch_ot_hours = round_ot_pay_hours(raw) if self.compensation == OT_PAY else raw
		if not self.shift:
			self.shift = frappe.db.get_value(
				"Attendance",
				{"employee": self.employee, "attendance_date": self.ot_date, "docstatus": ("<", 2)},
				"shift",
			)
		logger.info(
			"[ot_request] %s %s punch cap %sh (raw %.2f, comp %s)",
			self.employee,
			self.ot_date,
			self.punch_ot_hours,
			raw,
			self.compensation,
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
		# Replacement Leave is granted PER WORKING DAY, directly, on approval — no
		# bank, no accumulation, no separate claim. That day's OT converts to whole
		# 4h blocks (4h=½, 8h=1, 12h=1.5; under 4h earns nothing) and lands in the
		# employee's allocation now. A rejection reaches docstatus 1 too but grants
		# nothing (guarded on Approved). The allocation name is kept so a cancel can
		# reverse exactly this grant.
		if self.status == "Approved" and self.compensation == REPLACEMENT_LEAVE:
			days = replacement_leave_days(flt(self.claimed_hours), replacement_leave_hours_per_day())
			if days > 0:
				allocation = grant_replacement_leave(
					self.employee,
					self.employee_name,
					self.company,
					days,
					getdate(),
					description=self.explanation,
				)
				self.db_set("leave_allocation", allocation)
				# Store the ACTUAL days granted so a cancel reverses exactly this — a
				# recompute would drift if HR changes the hours-per-day ratio later.
				self.db_set("leave_days_granted", days)

	def on_cancel(self):
		# Reverse the per-day Replacement Leave grant this request made, if any. No
		# bank to reconcile any more — the days went straight into the allocation, so
		# cancelling takes back exactly what was GRANTED (the stored day count, never a
		# recompute, which would drift if HR changed the ratio since approval).
		logger.info(
			"[ot_request] cancel %s (comp %s, allocation %s, days %s)",
			self.name,
			self.compensation,
			self.leave_allocation,
			self.leave_days_granted,
		)
		if self.compensation == REPLACEMENT_LEAVE and self.leave_allocation and self.leave_days_granted:
			reverse_replacement_leave(self.leave_allocation, flt(self.leave_days_granted))


def get_replacement_leave_bank(employee: str, as_of=None, exclude_request: str | None = None) -> dict:
	"""Convertible replacement-leave hours in the LEAVE PERIOD covering `as_of` —
	approved replacement-leave OT worked in the period, minus hours reserved by
	claims filed in it (drafts included, so a pending claim can't be double-
	funded).

	The boundary is the LEAVE PERIOD, the same one add_to_leave_allocation scopes
	the granted days to — replacement leave is leave, and leave lives for its
	period. This is the coherent lifetime for the hours-bank too: they expire
	exactly when the leave they would become expires, not sooner. It replaces
	both the 2026-08-19 calendar-month bank (which expired hours FASTER than the
	days they convert to — the source of the backdated-OT stranding) and the
	interim 2-cycle window (that tied banked-leave lifetime to the OT-PAY payroll
	cutoff, a different concern). The 16th-to-15th filing window still governs
	which payroll pays OT; it does not govern how long banked leave lives.

	A leave period is a fixed range, so credits and debits are both bounded by it
	and hours_available cannot drift negative the way a rolling window could.
	When no active period covers `as_of` there is nothing to bank (a claim can't
	be approved without one either — see add_to_leave_allocation).

	DEPRECATED: Replacement Leave is now granted PER WORKING DAY, directly, on OT
	approval (OTRequest.on_submit) — nothing banks or accumulates, so there is no
	pool to convert. This returns an empty bank so the legacy Replacement Leave card
	and Claim show "nothing to do", and the function and doctype stay (not deleted)
	so any historical rows remain loadable. The old bank computation is removed — it
	is in git history if ever needed.
	"""
	logger.info("[ot_request] replacement-leave bank deprecated — empty for %s (per-day grant now)", employee)
	return {
		"period_start": None,
		"period_end": None,
		"hours_total": 0,
		"hours_claimed": 0,
		"hours_available": 0,
	}
