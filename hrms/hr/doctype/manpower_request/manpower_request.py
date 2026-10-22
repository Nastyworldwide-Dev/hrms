# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Manpower Request: a manager asks for staff; the line approves, then HR hires.

Shaped like Compensatory Leave Request (employee + Open/Approved/Rejected + submit) so every
Nadi approval list, count and reminder reads it with no special case. The decision is
`status`; what HR does afterwards is `hiring_status` (permlevel 1, HR only).

Owner rulings, 22 Oct 2026: only someone with a team sends one (HR may file for anyone);
the sender's own approval line decides, one level, then HR; the request is private to its
sender, the approver it was shared with, and HR (salary is on it).
"""

import logging

from dateutil.relativedelta import relativedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate

from hrms.hr.utils import (
	get_designated_approvers,
	sees_all_employee_data,
	share_doc_with_approver,
	validate_active_employee,
	validate_filing_for_self,
	validate_self_submission,
)
from hrms.mixins.pwa_notifications import PWANotificationsMixin
from hrms.utils.identity import get_employee, normalize_login

logger = logging.getLogger(__name__)

#: How soon the staff are needed -> how urgent it is. The one place the pairing lives
#: (owner, 22 Oct 2026); the Select's options must be exactly these keys.
URGENCY_BY_HOW_SOON = {
	"Within 2 weeks": "High",
	"3–4 weeks": "Medium",
	"1–2 months": "Low",
}

#: A replaced person who has already left still counts when they left this recently.
REPLACEMENT_LEAVER_MONTHS = 6

NOT_A_MANAGER = "Only someone with a team can request manpower."


def urgency_for(how_soon: str | None) -> str | None:
	"""High / Medium / Low for a "How soon" answer, or None for anything else."""
	return URGENCY_BY_HOW_SOON.get(how_soon)


def required_answer_gaps(rows) -> list[str]:
	"""The question of every required row whose answer is blank, in row order."""
	gaps = []
	for row in rows or []:
		if not cint(row.get("required")):
			continue
		answer = row.get("answer")
		if answer is None or not str(answer).strip():
			gaps.append(row.get("question"))
	return gaps


def can_file_manpower_request(employee: str | None) -> bool:
	"""May `employee` send a manpower request? HR may for anyone; everyone else needs an
	Active direct report (the same question hrms.api.team.has_team asks of the Team page)."""
	if sees_all_employee_data(frappe.session.user):
		return True
	return bool(employee and frappe.db.exists("Employee", {"reports_to": employee, "status": "Active"}))


class ManpowerRequest(Document, PWANotificationsMixin):
	def before_validate(self):
		# the sender, unless HR names someone else; runs before the mandatory check
		if not self.employee:
			self.employee = get_employee()

	def validate(self):
		validate_active_employee(self.employee)
		if self.is_new():
			# `employee` is set-only-once, so the subject is decided here and nowhere else
			validate_filing_for_self(self)
			if not can_file_manpower_request(self.employee):
				logger.warning("[manpower] %s has no team, refused", self.employee)
				frappe.throw(_(NOT_A_MANAGER), frappe.PermissionError)
		self.validate_headcount()
		self.validate_location()
		self.validate_replacement()
		self.urgency = urgency_for(self.how_soon)
		self.validate_start_date()
		self.validate_salaries()
		self.validate_answers()

	def validate_headcount(self):
		if cint(self.headcount) < 1:
			frappe.throw(_("Headcount must be at least 1."))

	def validate_location(self):
		# "Other" is no location plus a few words on where (the picker adds it client-side)
		if self.location:
			self.location_other = None
		elif not (self.location_other or "").strip():
			frappe.throw(_("Say where they will work."))

	def validate_replacement(self):
		if self.request_type != "Replacement":
			self.replacing_employee = None
			return
		if not self.replacing_employee:
			frappe.throw(_("Name the staff being replaced."))
		staff = frappe.db.get_value(
			"Employee", self.replacing_employee, ["department", "status", "relieving_date"], as_dict=True
		)
		if not staff or staff.department != self.department:
			frappe.throw(_("The staff being replaced must be in the {0} department.").format(self.department))
		if staff.status != "Active":
			earliest = getdate() - relativedelta(months=REPLACEMENT_LEAVER_MONTHS)
			if not staff.relieving_date or getdate(staff.relieving_date) < earliest:
				frappe.throw(
					_("The staff being replaced must be active or have left in the last {0} months.").format(
						REPLACEMENT_LEAVER_MONTHS
					)
				)

	def validate_start_date(self):
		"""After today, when the sender picks it. Not re-asked of a waiting request whose date
		simply arrived: Approve validates that draft too, and it must not be stopped by the clock."""
		if not self.start_date or cint(self.docstatus) != 0:
			return
		if not self.is_new():
			previous = self.get_doc_before_save()
			if not previous or getdate(previous.get("start_date")) == getdate(self.start_date):
				return
		if getdate(self.start_date) <= getdate():
			frappe.throw(_("The start date must be after today."))

	def validate_salaries(self):
		for field, label in (
			("budgeted_salary", _("Budgeted Salary")),
			("proposed_salary", _("Proposed Salary")),
		):
			if flt(self.get(field)) <= 0:
				frappe.throw(_("{0} must be more than zero.").format(label))

	def validate_answers(self):
		gaps = required_answer_gaps(self.answers)
		if gaps:
			frappe.throw(_("Please answer: {0}").format(", ".join(gaps)))

	def _get_doc_approver(self) -> str | None:
		"""The first person on the sender's approval line (leave pair, as Compensatory Leave)."""
		line = get_designated_approvers(self.employee, "leave_approver", "leave_approvers")
		return normalize_login(line[0]) if line else None

	def after_insert(self):
		# Once, when sent. The approver — usually holding only Employee — could not read it
		# otherwise; the share is that read (employee_owned_row_scope honours DocShare).
		approver = self._get_doc_approver()
		logger.info("[manpower] %s sent by %s, approver %s", self.name, self.employee, approver)
		share_doc_with_approver(self, approver)
		self.notify_approver()

	def on_submit(self):
		# the sender must never be the submitter, HR included (as Compensatory Leave Request)
		validate_self_submission(self)
		# decide() sets the status, then submits: a rejection reaches docstatus 1 too
		if self.status not in ("Approved", "Rejected"):
			frappe.throw(
				_("{0} must be Approved or Rejected before it can be submitted.").format(_(self.doctype))
			)
		logger.info("[manpower] %s %s by %s", self.name, self.status, frappe.session.user)
		if self.status == "Approved":
			self.db_set("hiring_status", "Waiting for HR")
