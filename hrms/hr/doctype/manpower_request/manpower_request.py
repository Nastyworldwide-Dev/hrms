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
from html import escape

from dateutil.relativedelta import relativedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.share import get_shared
from frappe.utils import cint, flt, getdate, now_datetime

from hrms.hr.utils import (
	get_designated_approvers,
	holds_hr_role,
	is_own_employee,
	sees_all_employee_data,
	share_doc_with_approver,
	validate_active_employee,
	validate_filing_for_self,
	validate_self_submission,
)
from hrms.mixins.pwa_notifications import PWANotificationsMixin
from hrms.overrides.remote_checkin_request_hooks import hr_alert_recipients
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

#: The sender may take a request back while HR has not finished with it (owner, 22 Oct 2026).
WITHDRAWABLE_HIRING = ("Waiting for HR", "Recruiting")

#: HR's last words on a request: only a System Manager reopens one of these.
CLOSED_HIRING = ("Filled", "Not proceeding")

#: Longest withdraw reason kept (characters). ceiling: 500, upgrade: staff report a cut-off reason
WITHDRAW_REASON_MAX = 500


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


def answers_from_settings(sent, questions) -> list[dict]:
	"""The answer rows a request keeps: one per ACTIVE question HR set, in HR's order, with HR's words,
	type and required flag; only the answer comes from the sender. Pure, so it is tested directly.

	Frappe review of the report slice (22 Oct 2026): the question text came from the phone, and the
	Desk report makes a column of every distinct question, so a hand-made request could add a junk
	column or markup to a header HR opens. A required question the sender left out entirely is still
	asked, so `required_answer_gaps` refuses it."""
	given = {(row.get("question") or "").strip(): row.get("answer") for row in sent or []}
	kept = []
	asked = set()
	for question in sorted(
		(q for q in questions or [] if cint(q.get("active"))), key=lambda q: q.get("idx") or 0
	):
		# both sides stripped: a Settings row saved as "KPIs " must still match (review of 301765fdf)
		words = (question.question or "").strip()
		asked.add(words)
		answer = given.get(words)
		kept.append(
			{
				"step": question.step,
				"question": words,
				"answer_type": question.answer_type,
				"required": 1 if cint(question.required) else 0,
				"answer": "" if answer is None else str(answer).strip(),
			}
		)
	# an answer to a question HR no longer asks (renamed or switched off after the wizard loaded) is
	# dropped; say so, so a lost answer is findable rather than silent
	dropped = [q for q, a in given.items() if q not in asked and str(a or "").strip()]
	if dropped:
		logger.warning("[manpower] dropped answers to questions no longer asked: %s", dropped)
	return kept


def board_group(status: str | None, hiring_status: str | None) -> str:
	"""The list a request sits in. Open waits on the manager; Approved waits on HR until HR picks it
	up (Waiting for HR, or nothing yet), then is Recruiting; every other ending is Done."""
	if status == "Open":
		return "waiting_manager"
	if status == "Approved" and hiring_status in (None, "", "Waiting for HR"):
		return "needs_hr"
	if status == "Approved" and hiring_status == "Recruiting":
		return "recruiting"
	return "done"


def request_age(request, today):
	"""(days open, the day it closed or None). A live request has been open since it was sent; a
	finished one stopped counting the day it was last touched (`modified`: a closed request is final,
	so that is the day it closed). Pure: the clock comes in as `today`. The Nadi board and the Desk
	report both read it, so the two never disagree."""
	closed = None
	if board_group(request.get("status"), request.get("hiring_status")) == "done":
		closed = getdate(request.get("modified"))
	return ((closed or today) - getdate(request.get("creation"))).days, closed


def _last_change(changes: list[dict], field: str, new: str) -> dict:
	"""The latest recorded change of `field` to `new`, or {}."""
	for change in reversed(changes or []):
		if change.get("field") == field and change.get("new") == new:
			return change
	return {}


def _step(key: str, label: str, state: str, who=None, at=None, note=None) -> dict:
	return {"key": key, "label": label, "who": who, "at": at, "state": state, "note": note or None}


def build_progress(request: dict, changes: list[dict]) -> list[dict]:
	"""The tracker: Sent -> Manager -> HR -> Filled, each step saying who, when and where it stands.

	Pure, over plain dicts, so it is tested directly. `request` carries employee_name, creation,
	status, docstatus, hiring_status, hr_note, approver_name, rejection_reason, withdrawn_reason,
	withdrawn_at. `changes` is the request's recorded history, oldest first, one dict per change of
	`status` or `hiring_status`: {field, old, new, by (a name), at}. state is done | current |
	waiting | rejected | withdrawn.
	"""
	status = request.get("status")
	hiring = request.get("hiring_status")
	withdrawn = status == "Withdrawn"
	# only an approved request can be withdrawn at docstatus 1, so that one WAS approved
	approved = status == "Approved" or (withdrawn and cint(request.get("docstatus")) == 1)
	sender = request.get("employee_name")
	gone = (sender, request.get("withdrawn_at"), request.get("withdrawn_reason"))

	steps = [_step("sent", _("Sent"), "done", sender, request.get("creation"))]

	decided = _last_change(changes, "status", "Approved" if approved else "Rejected")
	if status == "Rejected":
		manager = _step(
			"manager",
			_("Manager"),
			"rejected",
			decided.get("by"),
			decided.get("at"),
			request.get("rejection_reason"),
		)
	elif approved:
		manager = _step("manager", _("Manager"), "done", decided.get("by"), decided.get("at"))
	elif withdrawn:
		manager = _step("manager", _("Manager"), "withdrawn", *gone)
	else:
		manager = _step("manager", _("Manager"), "current", request.get("approver_name"))
	steps.append(manager)

	if not approved:
		hr = _step("hr", _("HR"), "waiting")
	elif withdrawn:
		hr = _step("hr", _("HR"), "withdrawn", *gone)
	elif hiring == "Not proceeding":
		said = _last_change(changes, "hiring_status", hiring)
		hr = _step("hr", _("HR"), "rejected", said.get("by"), said.get("at"), request.get("hr_note"))
	else:
		# Filled still names the HR person who started recruiting; Waiting for HR has nobody yet
		# (that value is written by the approver's submit, not by HR)
		moved = (
			_last_change(changes, "hiring_status", "Recruiting") if hiring in ("Recruiting", "Filled") else {}
		)
		hr = _step(
			"hr", _("HR"), "done" if hiring == "Filled" else "current", moved.get("by"), moved.get("at")
		)
	steps.append(hr)

	if approved and not withdrawn and hiring == "Filled":
		filled = _last_change(changes, "hiring_status", "Filled")
		steps.append(_step("filled", _("Filled"), "done", filled.get("by"), filled.get("at")))
	else:
		steps.append(_step("filled", _("Filled"), "waiting"))
	return steps


def can_file_manpower_request(employee: str | None) -> bool:
	"""May `employee` send a manpower request? HR may for anyone; everyone else needs an
	Active direct report (the same question hrms.api.team.has_team asks of the Team page)."""
	if sees_all_employee_data(frappe.session.user):
		return True
	return bool(employee and frappe.db.exists("Employee", {"reports_to": employee, "status": "Active"}))


class ManpowerRequest(Document, PWANotificationsMixin):
	def onload(self):
		"""Refuse the Desk form to anyone the row scope would not show it to.

		Frappe answers has_permission True for the literal Administrator before
		any app hook runs, so the fence in employee_owned_row_scope cannot stop
		Administrator opening the form. Salary is on it: the sender, the person
		it was shared with for approval, and HR only (owner, 29 Oct 2026)."""
		user = frappe.session.user
		if user != "Administrator":
			return
		if (
			holds_hr_role(user)
			or is_own_employee(self.employee)
			or self.name in get_shared(self.doctype, user)
		):
			return
		logger.warning("[manpower] %s refused %s: Administrator is not HR", user, self.name)
		frappe.throw(
			_("Only HR, the sender and the approver can open a manpower request."), frappe.PermissionError
		)

	def before_validate(self):
		# the sender, unless HR names someone else; runs before the mandatory check
		if not self.employee:
			self.employee = get_employee()

	def validate(self):
		validate_active_employee(self.employee)
		self.validate_not_withdrawn_by_save()
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
		if self.hiring_status and cint(self.docstatus) == 0:
			frappe.throw(_("Hiring status opens once the manager approves."))

	def validate_not_withdrawn_by_save(self):
		"""Withdrawn is reached through `withdraw()` only, which writes it past validate. A save
		that sets it is a decision-field write by someone who is not deciding."""
		previous = self.get_doc_before_save()
		if self.status == "Withdrawn" and (previous is None or previous.get("status") != "Withdrawn"):
			logger.warning("[manpower] %s: a save tried to set Withdrawn, refused", self.name)
			frappe.throw(_("Use Withdraw to take a request back."), frappe.PermissionError)

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
		# only while it is being written by its sender: HR's later edits to the settings never rewrite an
		# old request (the answers are a copy of what was asked when it was sent)
		if cint(self.docstatus) == 0 and self.status == "Open":
			questions = frappe.get_cached_doc("Manpower Request Settings").questions
			self.set("answers", answers_from_settings(self.answers, questions))
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
		waiting = self._user_name(approver) if approver else _("their manager")
		self._notify_hr(f"{self._who()} asked for {self._what()} ({self.department}). Waiting for {waiting}.")

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
		self.notify_approval_status()
		if self.status == "Approved":
			self._notify_hr(
				f"{self._user_name(frappe.session.user)} approved {self._what()} for {self._who()}. Your turn."
			)

	def before_update_after_submit(self):
		"""HR's hiring status: only on an approved request, final once Filled / Not proceeding."""
		if not self.has_value_changed("hiring_status"):
			return
		if not (cint(self.docstatus) == 1 and self.status == "Approved"):
			frappe.throw(_("Only an approved request has a hiring status."))
		if not self.hiring_status:
			frappe.throw(_("Pick a hiring status."))
		previous = self.get_doc_before_save()
		was = previous.get("hiring_status") if previous else None
		if was in CLOSED_HIRING and "System Manager" not in frappe.get_roles():
			frappe.throw(
				_("This request is closed ({0}). Only a System Manager can reopen it.").format(_(was))
			)
		if self.hiring_status == "Not proceeding" and not (self.hr_note or "").strip():
			frappe.throw(_("Say why it is not proceeding."))

	def on_update_after_submit(self):
		"""Tell the sender when HR moves the hiring status (and why, when HR wrote a note)."""
		if not self.has_value_changed("hiring_status"):
			return
		to_user = self._get_employee_user()
		if not to_user or normalize_login(to_user) == normalize_login(frappe.session.user):
			return
		# the answer first, in words (design review of aba0a4461); the notice links to the record
		text = {
			"Recruiting": f"HR is recruiting for {self._what()}.",
			"Filled": f"{self._what()} is filled.",
			"Not proceeding": f"HR is not proceeding with {self._what()}.",
		}.get(self.hiring_status, f"{self._what()}: {self.hiring_status}.")
		note = (self.hr_note or "").strip()
		if note:
			# a refusal is followed by its reason; any other update by HR's remark
			text = f"{text[:-1]}: {note}" if self.hiring_status == "Not proceeding" else f"{text} {note}"
		self._send_notice(to_user, text)

	def withdraw(self, reason: str | None = None) -> None:
		"""The sender takes the request back. The record is kept.

		Written with db_set, past validate: Withdrawn is not a decision, so the decision-field
		guard has nothing to say, and `status` need not be editable after submit. A plain save
		that sets Withdrawn is refused (validate_not_withdrawn_by_save); this is the one door.
		"""
		if not is_own_employee(self.employee):
			logger.warning(
				"[manpower] %s: %s is not the sender, withdraw refused", self.name, frappe.session.user
			)
			frappe.throw(_("Only the person who sent this request can withdraw it."), frappe.PermissionError)
		was_open = cint(self.docstatus) == 0 and self.status == "Open"
		approved_live = (
			cint(self.docstatus) == 1
			and self.status == "Approved"
			and self.hiring_status in WITHDRAWABLE_HIRING
		)
		if not (was_open or approved_live):
			frappe.throw(_("This request can no longer be withdrawn."))
		reason = (reason or "").strip()[:WITHDRAW_REASON_MAX] or None
		self.db_set({"status": "Withdrawn", "withdrawn_reason": reason, "withdrawn_at": now_datetime()})
		logger.info("[manpower] %s withdrawn by %s (was open: %s)", self.name, frappe.session.user, was_open)
		message = f"{self._who()} withdrew the request for {self._what()}."
		approver = self._get_doc_approver() if was_open else None
		if approver and normalize_login(approver) != normalize_login(frappe.session.user):
			self._send_notice(approver, message)
		self._notify_hr(message)

	def _who(self) -> str:
		return self.employee_name or self.employee

	def _what(self) -> str:
		"""The title with the count after it, the mockup's form; just the title for one."""
		count = cint(self.headcount)
		return f"{self.position_title} ×{count}" if count > 1 else self.position_title

	def _user_name(self, user: str) -> str:
		return frappe.db.get_value("User", user, "full_name") or user

	def _send_notice(self, to_user: str, message: str) -> bool:
		"""One PWA Notification about this request. Plain text, escaped, in the Text Editor's <p>
		(a bare string is stripped to nothing there). Logged and False when it cannot be written:
		a notice must not undo the work around it."""
		try:
			notice = frappe.new_doc("PWA Notification")
			notice.from_user = frappe.session.user
			notice.to_user = to_user
			notice.message = f"<p>{escape(message, quote=False)}</p>"
			notice.reference_document_type = self.doctype
			notice.reference_document_name = self.name
			notice.insert(ignore_permissions=True)
			return True
		except Exception:
			logger.exception("[manpower] could not tell %s about %s", to_user, self.name)
			return False

	def _notify_hr(self, message: str) -> int:
		"""Every enabled HR Manager / HR User whose company fence admits this request, minus the
		sender. Returns how many were told."""
		# never raises: a notice must not undo the send, the decision or the withdraw around it
		try:
			company = self.company or frappe.db.get_value("Employee", self.employee, "company")
			sender = normalize_login(self._get_employee_user())
			recipients = [user for user in hr_alert_recipients(company) if normalize_login(user) != sender]
		except Exception:
			logger.exception("[manpower] %s: could not resolve HR recipients", self.name)
			return 0
		told = sum(self._send_notice(user, message) for user in recipients)
		logger.info("[manpower] %s: HR told (%d) for company %s", self.name, told, company)
		return told
