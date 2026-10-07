# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.model.workflow import get_workflow_name
from frappe.query_builder.functions import Sum
from frappe.utils import cstr, flt, fmt_money, formatdate, get_link_to_form, getdate, today

import erpnext
from erpnext.accounts.doctype.repost_accounting_ledger.repost_accounting_ledger import (
	validate_docs_for_voucher_types,
)
from erpnext.accounts.doctype.sales_invoice.sales_invoice import get_bank_cash_account
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts.utils import (
	create_gain_loss_journal,
	unlink_ref_doc_from_payment_entries,
)
from erpnext.controllers.accounts_controller import AccountsController

import hrms
from hrms.hr.utils import (
	set_employee_name,
	share_doc_with_approver,
	validate_active_employee,
	validate_staff_approver,
)
from hrms.mixins.pwa_notifications import PWANotificationsMixin
from hrms.overrides.employee_company_default import set_company_from_employee

logger = logging.getLogger(__name__)


class InvalidExpenseApproverError(frappe.ValidationError):
	pass


class ExpenseApproverIdentityError(frappe.ValidationError):
	pass


class MismatchError(frappe.ValidationError):
	pass


class ExpenseClaim(AccountsController, PWANotificationsMixin):
	def onload(self):
		self.set_onload(
			"self_expense_approval_not_allowed",
			frappe.db.get_single_value("HR Settings", "prevent_self_expense_approval"),
		)

	def after_insert(self):
		self.notify_approver()

	def validate(self):
		# The Employee's company, never the client's: the company link ignores User Permissions
		# so a named approver in another company can open the claim (40d3760a3).
		set_company_from_employee(self)
		self.set_posting_date()
		validate_active_employee(self.employee)
		set_employee_name(self)
		self.set_payable_account()
		self.validate_staff_approver()
		self.set_sanctioned_amount_default()
		self.validate_sanctioned_amount()
		self.calculate_total_amount()
		self.validate_no_duplicate_expenses()
		self.validate_advances()
		self.set_expense_account(validate=True)
		self.set_default_accounting_dimension()
		self.calculate_taxes()
		self.set_status()
		self.validate_company_and_department()
		self.validate_cost_center_company()
		if self.task and not self.project:
			self.project = frappe.db.get_value("Task", self.task, "project")

		if flt(self.grand_total) > 0 and self.total_advance_amount:
			self.is_paid = 0

	def set_status(self, update=False):
		status = {"0": "Draft", "1": "Submitted", "2": "Cancelled"}[cstr(self.docstatus or 0)]

		precision = self.precision("grand_total")

		if self.docstatus == 1:
			if self.approval_status == "Approved":
				if (
					# set as paid
					self.is_paid
					or (
						flt(self.total_sanctioned_amount) > 0
						and (
							# grand total is reimbursed
							(flt(self.grand_total, precision) == flt(self.total_amount_reimbursed, precision))
							# grand total (to be paid) is 0 since linked advances already cover the claimed amount
							or (flt(self.grand_total, precision) == 0)
						)
					)
				):
					status = "Paid"
				elif flt(self.total_sanctioned_amount) > 0:
					status = "Unpaid"
			elif self.approval_status == "Rejected":
				status = "Rejected"

		if update:
			self.db_set("status", status)
			self.publish_update()
			self.notify_update()
		else:
			self.status = status

	def set_posting_date(self):
		"""A claim filed without a posting date is posted today.

		The PWA form has no posting-date input (the field lives in the Desk
		form's Accounting tab), so a claim can arrive with the date empty.
		Frappe's own "Today" default fills only an ABSENT field; one sent as ""
		reached the mandatory check and refused the whole claim (15 Sep 2026).
		"""
		if self.posting_date:
			return
		self.posting_date = today()
		frappe.logger("hrms").info("[expense_claim] %s: posting date defaulted to today", self.name)

	def set_payable_account(self):
		"""Default the payable account the way the Desk form does, server-side.

		The PWA form leaves it to company defaults, and a company shell
		(hrms/sync/company_shells.py) has no `default_expense_claim_payable_account`
		— ERPNext only ever sets `default_payable_account`. Without this the claim
		saves as a draft and dies at approval with "Account is required" (GL
		posting), which is what HR saw on 9 September 2026.
		"""
		# Paid or not: both GL paths post to payable_account (the JSON's
		# mandatory_depends_on says otherwise and is wrong about the ledger).
		if self.payable_account or not self.company:
			return
		self.payable_account = expense_claim_payable_account(
			frappe.get_cached_value(
				"Company",
				self.company,
				["default_expense_claim_payable_account", "default_payable_account"],
				as_dict=True,
			)
		)
		if self.payable_account:
			frappe.logger("hrms").info(
				"[expense_claim] %s: payable account defaulted to %s", self.name, self.payable_account
			)

	def validate_company_and_department(self):
		if self.department:
			company = frappe.db.get_value("Department", self.department, "company")
			if company and self.company != company:
				frappe.throw(
					_("Department {0} does not belong to company: {1}").format(self.department, self.company),
					exc=MismatchError,
				)

	def validate_cost_center_company(self):
		"""Every cost tag on the claim belongs to the claim's company.

		The PWA offers only the company's own cost centers
		(hrms.api.get_expense_cost_tags); this is the fence behind the picker,
		so a hand-built payload cannot tag a line with another company's cost
		center. GL would refuse it much later, at submit, in the approver's lap.
		"""
		tags = [(_("Claim"), self.cost_center)]
		tags += [(_("Row #{0}").format(row.idx), row.cost_center) for row in self.expenses or []]
		for where, cost_center in tags:
			if not cost_center:
				continue
			owner = frappe.get_cached_value("Cost Center", cost_center, "company")
			if owner and owner != self.company:
				frappe.throw(
					_("{0}: Cost Center {1} belongs to {2}, not {3}").format(
						where, cost_center, owner, self.company
					),
					exc=MismatchError,
				)

	def validate_staff_approver(self):
		validate_staff_approver(self, "expense_approver", "expense_approver", "expense_approvers")

	def set_sanctioned_amount_default(self):
		"""A NEW line with an amount and no sanctioned amount is sanctioned in full.

		Desk's form script and Nadi's ExpensesTable.vue both copy amount into
		sanctioned_amount as the user types; the server never did, so a claim
		filed through the API without it was approved paying nothing — total
		sanctioned 0, no GL, nothing to tell the approver (fresh.local, 15 Sep
		2026). Only a new claim is defaulted: an approver who reduces a line to
		0 on purpose is editing an existing row and is left alone.
		"""
		if not self.is_new():
			return
		for row in self.get("expenses"):
			if flt(row.amount) and not flt(row.sanctioned_amount):
				logger.info(
					"[expense_claim] %s: sanctioned_amount defaulted to amount %s", self.name, row.amount
				)
				row.sanctioned_amount = row.amount

	def _new_expense_lines(self, precision) -> set:
		"""The (type, date, amount) lines this save adds or changes. On a new claim that is every
		line. An unchanged line keeps its place in time: it is the original against later copies,
		while a line just added or edited is compared with every claim (an old draft edited to
		copy a newer claim is a new expense in all but name)."""
		# a claim with no stored copy (new, or saved by code that skipped the load) has only new lines
		before = None if self.is_new() else self.get_doc_before_save()

		def keys(doc):
			return {
				(row.expense_type, getdate(row.expense_date), flt(row.amount, precision))
				for row in doc.get("expenses")
				if row.expense_type and row.expense_date and getdate(row.expense_date)
			}

		mine = keys(self)
		return mine - keys(before) if before else mine

	def validate_no_duplicate_expenses(self):
		"""Refuse an expense that is already claimed; warn about one that looks like it.

		Owner ruling R1 (6 Oct 2026): block exact duplicates, warn on near ones.
		Exact = same expense type, date and amount as a line of this claim or of
		another LIVE claim of the same employee (not cancelled, not Rejected).
		Near = same type and date, different amount: saved, with a warning. The
		claim this one amends is not a duplicate of it. One query covers every
		line, whatever the number of lines.

		A claim that is itself Rejected or cancelled is not checked, so an
		approver can always reject a duplicate that was filed before this rule.
		"""
		if not self._checks_for_duplicates():
			return

		precision = self.precision("amount", "expenses")
		lines = self._dated_expense_lines(precision)
		if not lines:
			return

		claimed = {}
		for idx, expense_type, date, amount in lines:
			if (expense_type, date, amount) in claimed:
				logger.info(
					"[expense_claim] %s: refused, row %s repeats row %s",
					self.name,
					idx,
					claimed[(expense_type, date, amount)],
				)
				frappe.throw(
					_(
						"Rows {0} and {1} are the same expense ({2}, {3}, {4}). Remove one, or change the description and amount."
					).format(
						claimed[(expense_type, date, amount)],
						idx,
						expense_type,
						formatdate(date),
						fmt_money(amount, precision),
					)
				)
			claimed[(expense_type, date, amount)] = idx

		others = self._other_claim_lines(lines)

		# Which claim is the original? An unchanged line of this claim only clashes with an EARLIER
		# claim (same second: the lower name), so the first claim can still be approved when a later
		# copy exists. A new or edited line clashes with every claim.
		fresh = self._new_expense_lines(precision)
		mine_created = str(self.creation or "")

		def earlier(other):
			theirs = str(other.creation or "")
			return theirs < mine_created or (theirs == mine_created and other.name < (self.name or ""))

		for other in others:
			date = getdate(other.expense_date)
			amount = flt(other.amount, precision)
			key = (other.expense_type, date, amount)
			if key in claimed and (key in fresh or earlier(other)):
				logger.info("[expense_claim] %s: refused, same expense as %s", self.name, other.name)
				frappe.throw(
					_(
						"This expense is already claimed on {0} ({1}, {2}, {3}). If it is a different expense, change the description and amount, or ask HR."
					).format(
						get_link_to_form("Expense Claim", other.name),
						other.expense_type,
						formatdate(date),
						fmt_money(amount, precision),
					)
				)

		# name only claims the person saving may open: an approver saving on Desk must not
		# learn the names of the employee's claims routed to someone else (alpha.38 review)
		near = [
			n
			for n in near_duplicate_claims(others, lines)
			if frappe.has_permission("Expense Claim", ptype="read", doc=n[2])
		]
		if near:
			logger.info("[expense_claim] %s: warned of %s near duplicate(s)", self.name, len(near))
			frappe.msgprint(
				"<br>".join(
					near_duplicate_sentences(near, lambda name: get_link_to_form("Expense Claim", name))
				),
				indicator="orange",
			)

	def near_duplicate_notes(self, may_open=lambda name: True) -> list[str]:
		"""The warning `validate_no_duplicate_expenses` shows, for a claim already saved.

		Nadi never shows a msgprint (frappe-ui drops `_server_messages` on a
		successful request), so `hrms.api.near_duplicate_expenses` asks for the
		same sentences here, by the same rule and in plain text (the claim is
		named, not linked to a Desk page an employee cannot open). `may_open`
		keeps out a claim the caller may not open: an approver of this claim
		does not learn the names of claims routed to someone else.
		"""
		if not self._checks_for_duplicates():
			return []
		lines = self._dated_expense_lines(self.precision("amount", "expenses"))
		if not lines:
			return []
		near = near_duplicate_claims(self._other_claim_lines(lines), lines)
		return near_duplicate_sentences([n for n in near if may_open(n[2])])

	def _checks_for_duplicates(self) -> bool:
		"""A claim that is itself Rejected or cancelled is not checked (see validate_no_duplicate_expenses)."""
		return not (self.docstatus == 2 or self.approval_status in ("Rejected", "Cancelled"))

	def _dated_expense_lines(self, precision) -> list[tuple]:
		"""(idx, type, date, amount) of each line that has a type and a readable date."""
		lines = [
			(row.idx, row.expense_type, getdate(row.expense_date), flt(row.amount, precision))
			for row in self.get("expenses")
			if row.expense_type and row.expense_date
		]
		# an unreadable date is Frappe's own error to raise; it is not a duplicate
		return [line for line in lines if line[2]]

	def _other_claim_lines(self, lines) -> list:
		"""Every expense line of this employee's other live claims on the dates of `lines`: ONE query."""
		return frappe.db.sql(
			"""
			select ec.name, ec.creation, ecd.expense_type, ecd.expense_date, ecd.amount
			from `tabExpense Claim` ec
			join `tabExpense Claim Detail` ecd
				on ecd.parent = ec.name and ecd.parenttype = 'Expense Claim' and ecd.parentfield = 'expenses'
			where ec.employee = %(employee)s
				and ec.docstatus != 2
				and ifnull(ec.approval_status, '') != 'Rejected'
				and ec.name not in (%(this)s, %(amended)s)
				and ecd.expense_date in %(dates)s
			order by ec.creation, ec.name, ecd.idx
			""",
			{
				"employee": self.employee,
				"this": self.name or "",
				"amended": self.amended_from or "",
				"dates": tuple(sorted({date.isoformat() for _idx, _type, date, _amount in lines})),
			},
			as_dict=True,
		)

	def validate_for_self_approval(self):
		"""The Desk twin of `hrms.api.approval._decision_access` — see the
		Leave Application version for the 17 Sep 2026 report behind it.

		The chain-of-command refusal is scoped to an APPROVED claim on purpose:
		submitting a claim of your own is how it is filed, and blocking that
		would stop people claiming at all. The tickbox keeps its existing,
		wider meaning untouched.
		"""
		from hrms.hr.utils import has_approver_above, is_own_employee

		if not is_own_employee(self.employee) or get_workflow_name("Expense Claim"):
			return

		if self.approval_status == "Approved" and has_approver_above(self.employee, "Expense Claim"):
			frappe.throw(_("Your own expense claim is decided by your approver, not by you."))

		if frappe.db.get_single_value("HR Settings", "prevent_self_expense_approval"):
			frappe.throw(_("Self-approval for Expense Claims is not allowed"))

	def on_update(self):
		share_doc_with_approver(self, self.expense_approver)
		self.publish_update()

	def after_delete(self):
		self.publish_update()

	def on_discard(self):
		self.db_set("status", "Cancelled")
		self.db_set("approval_status", "Cancelled")

	def before_submit(self):
		self.validate_for_self_approval()

	def publish_update(self):
		employee_user = frappe.db.get_value("Employee", self.employee, "user_id", cache=True)
		hrms.refetch_resource("hrms:my_claims", employee_user)
		hrms.refetch_resource("hrms:team_claims")

	def on_submit(self):
		if self.approval_status == "Draft":
			frappe.throw(_("""Approval Status must be 'Approved' or 'Rejected'"""))

		# Told on submit, not on a draft save: only now is the decision transacted.
		self.notify_approval_status()
		self.update_task_and_project()
		self.make_gl_entries()
		update_reimbursed_amount(self)
		self.update_claimed_amount_in_employee_advance()
		self.create_exchange_gain_loss_je()

	def on_update_after_submit(self):
		if self.check_if_fields_updated([], {"taxes": ("account_head",), "expenses": ()}):
			validate_docs_for_voucher_types(["Expense Claim"])
			self.repost_accounting_entries()

	def on_cancel(self):
		self.update_task_and_project()
		self.ignore_linked_doctypes = (
			"GL Entry",
			"Stock Ledger Entry",
			"Payment Ledger Entry",
			"Advance Payment Ledger Entry",
		)
		if self.payable_account:
			self.make_gl_entries(cancel=True)

		update_reimbursed_amount(self)

		self.update_claimed_amount_in_employee_advance()
		self.publish_update()
		unlink_ref_doc_from_payment_entries(self)

	def update_claimed_amount_in_employee_advance(self):
		for d in self.get("advances"):
			frappe.get_doc("Employee Advance", d.employee_advance).update_claimed_amount()

	def update_task_and_project(self):
		if self.task:
			task = frappe.get_doc("Task", self.task)

			ExpenseClaim = frappe.qb.DocType("Expense Claim")
			task.total_expense_claim = (
				frappe.qb.from_(ExpenseClaim)
				.select(Sum(ExpenseClaim.total_sanctioned_amount))
				.where(
					(ExpenseClaim.docstatus == 1)
					& (ExpenseClaim.project == self.project)
					& (ExpenseClaim.task == self.task)
				)
			).run()[0][0]

			task.save()

		for project in self.get_linked_projects():
			frappe.get_doc("Project", project).update_project()

	def get_linked_projects(self):
		projects = set()
		if self.project:
			projects.add(self.project)
		projects.update(expense.project for expense in self.expenses if expense.project)
		return projects

	def make_gl_entries(self, cancel=False):
		if flt(self.total_sanctioned_amount) > 0:
			gl_entries = self.get_gl_entries()
			make_gl_entries(gl_entries, cancel)

	def get_gl_entries(self):
		gl_entry = []
		self.validate_account_details()

		# payable entry
		if self.grand_total:
			gl_entry.append(
				self.get_gl_dict(
					{
						"account": self.payable_account,
						"credit": self.base_grand_total,
						"credit_in_account_currency": self.grand_total,
						"credit_in_transaction_currency": self.grand_total,
						"against": ",".join([d.default_account for d in self.expenses]),
						"party_type": "Employee",
						"party": self.employee,
						"against_voucher_type": self.doctype,
						"against_voucher": self.name,
						"cost_center": self.cost_center,
						"project": self.project,
						"transaction_exchange_rate": self.exchange_rate,
					},
					account_currency=self.currency,
					item=self,
				)
			)

		# expense entries
		for data in self.expenses:
			gl_entry.append(
				self.get_gl_dict(
					{
						"account": data.default_account,
						"debit": data.base_sanctioned_amount,
						"debit_in_account_currency": data.sanctioned_amount,
						"debit_in_transaction_currency": data.sanctioned_amount,
						"against": self.employee,
						"cost_center": data.cost_center or self.cost_center,
						"project": data.project or self.project,
						"transaction_exchange_rate": self.exchange_rate,
					},
					account_currency=self.currency,
					item=data,
				)
			)

		# gl entry against advance
		for data in self.advances:
			if data.allocated_amount:
				gl_entry.append(
					self.get_gl_dict(
						{
							"account": data.advance_account,
							"credit": data.base_allocated_amount,
							"credit_in_account_currency": data.allocated_amount,
							"credit_in_transaction_currency": data.allocated_amount,
							"against": ",".join([d.default_account for d in self.expenses]),
							"party_type": "Employee",
							"party": self.employee,
							"against_voucher_type": data.reference_type,
							"against_voucher": data.reference_name,
							"advance_voucher_type": data.reference_type,
							"advance_voucher_no": data.reference_name,
							"transaction_exchange_rate": self.exchange_rate,
							"cost_center": self.cost_center,
							"project": self.project,
						},
						account_currency=self.currency,
					)
				)

		self.add_tax_gl_entries(gl_entry)

		if self.is_paid and self.grand_total:
			# payment entry
			payment_account = get_bank_cash_account(self.mode_of_payment, self.company).get("account")
			gl_entry.append(
				self.get_gl_dict(
					{
						"account": payment_account,
						"credit": self.base_grand_total,
						"credit_in_account_currency": self.grand_total,
						"credit_in_transaction_currency": self.grand_total,
						"against": self.employee,
						"transaction_exchange_rate": self.exchange_rate,
						"cost_center": self.cost_center,
						"project": self.project,
					},
					account_currency=self.currency,
					item=self,
				)
			)

			gl_entry.append(
				self.get_gl_dict(
					{
						"account": self.payable_account,
						"party_type": "Employee",
						"party": self.employee,
						"against": payment_account,
						"debit": self.base_grand_total,
						"debit_in_account_currency": self.grand_total,
						"debit_in_transaction_currency": self.grand_total,
						"against_voucher": self.name,
						"against_voucher_type": self.doctype,
						"transaction_exchange_rate": self.exchange_rate,
						"cost_center": self.cost_center,
						"project": self.project,
					},
					account_currency=self.currency,
					item=self,
				)
			)

		return gl_entry

	def add_tax_gl_entries(self, gl_entries):
		# tax table gl entries
		for tax in self.get("taxes"):
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": tax.account_head,
						"debit": tax.base_tax_amount,
						"debit_in_account_currency": tax.tax_amount,
						"debit_in_transaction_currency": tax.tax_amount,
						"against": self.employee,
						"cost_center": tax.cost_center or self.cost_center,
						"project": tax.project or self.project,
						"against_voucher_type": self.doctype,
						"against_voucher": self.name,
						"transaction_exchange_rate": self.exchange_rate,
					},
					account_currency=self.currency,
					item=tax,
				)
			)

	def set_default_accounting_dimension(self):
		from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
			get_checks_for_pl_and_bs_accounts,
		)

		for dim in get_checks_for_pl_and_bs_accounts():
			if dim.company != self.company:
				continue

			field = frappe.scrub(dim.fieldname)

			if self.meta.get_field(field):
				if not self.get(field) and dim.mandatory_for_bs:
					self.set(field, dim.default_dimension)

			for row in self.get("expenses") or []:
				if row.meta.get_field(field):
					if not row.get(field) and dim.mandatory_for_pl:
						row.set(field, dim.default_dimension)

	def create_exchange_gain_loss_je(self):
		if not self.advances:
			return

		per_advance_gain_loss = 0
		total_advance_exchange_gain_loss = 0
		for advance in self.advances:
			if advance.base_allocated_amount and self.base_total_advance_amount:
				allocated_amount_in_adv_exchange_rate = flt(advance.allocated_amount) * flt(
					advance.exchange_rate
				)
				per_advance_gain_loss += flt(
					(advance.base_allocated_amount - allocated_amount_in_adv_exchange_rate),
					self.precision("total_exchange_gain_loss"),
				)

				if per_advance_gain_loss:
					advance.db_set("exchange_gain_loss", per_advance_gain_loss)
					total_advance_exchange_gain_loss += per_advance_gain_loss
		if total_advance_exchange_gain_loss:
			gain_loss_account = frappe.get_cached_value("Company", self.company, "exchange_gain_loss_account")
			self.db_set(
				{
					"total_exchange_gain_loss": total_advance_exchange_gain_loss,
					"gain_loss_account": gain_loss_account,
				}
			)
			dr_or_cr = "credit" if self.total_exchange_gain_loss > 0 else "debit"
			reverse_dr_or_cr = "debit" if dr_or_cr == "credit" else "credit"

			je = create_gain_loss_journal(
				company=self.company,
				posting_date=today(),
				party_type="Employee",
				party=self.employee,
				party_account=self.payable_account,
				gain_loss_account=self.gain_loss_account,
				exc_gain_loss=self.total_exchange_gain_loss,
				dr_or_cr=dr_or_cr,
				reverse_dr_or_cr=reverse_dr_or_cr,
				ref1_dt=self.doctype,
				ref1_dn=self.name,
				ref1_detail_no=1,
				ref2_dt=self.doctype,
				ref2_dn=self.name,
				ref2_detail_no=1,
				cost_center=self.cost_center,
				dimensions={},
			)
			frappe.msgprint(
				_("All Exchange Gain/Loss amount of {0} has been booked through {1}").format(
					self.name,
					get_link_to_form("Journal Entry", je),
				)
			)

	def validate_account_details(self):
		for data in self.expenses:
			if not data.cost_center:
				frappe.throw(
					_("Row {0}: {1} is required in the expenses table to book an expense claim.").format(
						data.idx, frappe.bold(_("Cost Center"))
					)
				)

		if self.is_paid:
			if not self.mode_of_payment:
				frappe.throw(_("Mode of payment is required to make a payment").format(self.employee))

	def calculate_total_amount(self):
		self.total_claimed_amount = 0
		self.total_sanctioned_amount = 0

		for d in self.get("expenses"):
			self.round_floats_in(d)

			if self.approval_status == "Rejected":
				d.sanctioned_amount = 0.0

			self.total_claimed_amount += flt(d.amount)
			self.total_sanctioned_amount += flt(d.sanctioned_amount)
			self.set_base_fields_amount(d, ["amount", "sanctioned_amount"])

		self.set_base_fields_amount(self, ["total_sanctioned_amount", "total_claimed_amount"])

	def set_base_fields_amount(self, doc, fields, exchange_rate=None):
		"""set values in base currency"""
		for f in fields:
			val = flt(
				flt(doc.get(f), doc.precision(f))
				* flt(exchange_rate if exchange_rate else self.exchange_rate),
				doc.precision("base_" + f),
			)
			doc.set("base_" + f, val)

	@frappe.whitelist()
	def calculate_taxes(self):
		self.total_taxes_and_charges = 0
		for tax in self.taxes:
			self.round_floats_in(tax)

			if tax.rate:
				tax.tax_amount = flt(
					flt(self.total_sanctioned_amount) * flt(flt(tax.rate) / 100),
					tax.precision("tax_amount"),
				)

			tax.total = flt(tax.tax_amount) + flt(self.total_sanctioned_amount)
			self.total_taxes_and_charges += flt(tax.tax_amount)
			self.set_base_fields_amount(tax, ["tax_amount", "total"])

		self.round_floats_in(self, ["total_taxes_and_charges"])

		self.grand_total = (
			flt(self.total_sanctioned_amount)
			+ flt(self.total_taxes_and_charges)
			- flt(self.total_advance_amount)
		)
		self.round_floats_in(self, ["grand_total"])
		self.set_base_fields_amount(self, ["grand_total"])

	def validate_advances(self):
		self.total_advance_amount = 0
		precision = self.precision("total_advance_amount")

		for d in self.get("advances"):
			advance_employee = frappe.db.get_value("Employee Advance", d.employee_advance, "employee")
			if self.employee != advance_employee:
				frappe.throw(_("Selected employee advance is not of employee {}").format(self.employee))

			self.round_floats_in(d)
			if d.allocated_amount and flt(d.allocated_amount) > flt(
				flt(d.unclaimed_amount) - flt(d.return_amount), precision
			):
				frappe.throw(
					_("Row {0}# Allocated amount {1} cannot be greater than unclaimed amount {2}").format(
						d.idx, d.allocated_amount, d.unclaimed_amount
					)
				)

			self.total_advance_amount += flt(d.allocated_amount)
			self.set_base_fields_amount(d, ["advance_paid", "unclaimed_amount"], d.exchange_rate)
			self.set_base_fields_amount(d, ["allocated_amount"])

		if self.total_advance_amount:
			self.round_floats_in(self, ["total_advance_amount"])
			amount_with_taxes = flt(
				(flt(self.total_sanctioned_amount, precision) + flt(self.total_taxes_and_charges, precision)),
				precision,
			)
			self.set_base_fields_amount(self, ["total_advance_amount"])

			if flt(self.total_advance_amount, precision) > amount_with_taxes:
				frappe.throw(_("Total advance amount cannot be greater than total sanctioned amount"))

	def validate_sanctioned_amount(self):
		for d in self.get("expenses"):
			if flt(d.sanctioned_amount) > flt(d.amount):
				frappe.throw(
					_("Sanctioned Amount cannot be greater than Claim Amount in Row {0}.").format(d.idx)
				)

	def set_expense_account(self, validate=False):
		for expense in self.expenses:
			if not expense.default_account or not validate:
				expense.default_account = get_expense_claim_account(expense.expense_type, self.company)[
					"account"
				]


def near_duplicate_claims(others, lines) -> list[tuple]:
	"""(expense type, date, claim name) of each claim in `others` that holds a line of the same
	type and date as one of `lines`, whatever its amount; each once, in the order of `others`."""
	wanted = {(expense_type, date) for _idx, expense_type, date, _amount in lines}
	near = {}
	for other in others:
		date = getdate(other.expense_date)
		if (other.expense_type, date) in wanted:
			near.setdefault((other.expense_type, date, other.name), None)
	return list(near)

def near_duplicate_sentences(near, link=lambda name: name) -> list[str]:
	"""One plain sentence per near duplicate; `link` turns a claim name into what is shown for it."""
	return [
		_("You already claimed a {0} on {1} in {2}. Check it is not the same expense.").format(
			expense_type, formatdate(date), link(name)
		)
		for expense_type, date, name in near
	]

def update_reimbursed_amount(doc):
	total_amount_reimbursed = get_total_reimbursed_amount(doc)

	doc.total_amount_reimbursed = total_amount_reimbursed
	frappe.db.set_value("Expense Claim", doc.name, "total_amount_reimbursed", total_amount_reimbursed)

	doc.set_status(update=True)


def get_total_reimbursed_amount(doc):
	if doc.is_paid:
		# No need to check for cancelled state here as it will anyways update status as cancelled
		return doc.grand_total
	else:
		JournalEntryAccount = frappe.qb.DocType("Journal Entry Account")
		amount_via_jv = frappe.db.get_value(
			"Journal Entry Account",
			{"reference_name": doc.name, "docstatus": 1},
			Sum(
				JournalEntryAccount.debit_in_account_currency - JournalEntryAccount.credit_in_account_currency
			),
		)

		amount_via_payment_entry = frappe.db.get_value(
			"Payment Entry Reference",
			{
				"reference_name": doc.name,
				"advance_voucher_type": None,
				"docstatus": 1,
			},
			[{"SUM": "allocated_amount"}],
		)

		return flt(amount_via_jv) + flt(amount_via_payment_entry)


def get_outstanding_amount_for_claim(claim):
	precision = frappe.get_precision("Expense Claim", "grand_total")

	if isinstance(claim, str):
		claim = frappe.db.get_value(
			"Expense Claim",
			claim,
			(
				"total_sanctioned_amount",
				"total_taxes_and_charges",
				"total_amount_reimbursed",
				"total_advance_amount",
			),
			as_dict=True,
		)

	outstanding_amt = (
		flt(claim.total_sanctioned_amount)
		+ flt(claim.total_taxes_and_charges)
		- flt(claim.total_amount_reimbursed)
		- flt(claim.total_advance_amount)
	)

	return flt(outstanding_amt, precision)


def expense_claim_payable_account(company_defaults) -> str | None:
	"""The account an expense claim owes the employee through: the company's
	expense-claim payable if set, else its ordinary payable (Creditors). Pure."""
	defaults = company_defaults or {}
	return defaults.get("default_expense_claim_payable_account") or defaults.get("default_payable_account")


@frappe.whitelist()
def get_expense_claim_account_and_cost_center(expense_claim_type: str, company: str) -> dict:
	data = get_expense_claim_account(expense_claim_type, company)
	cost_center = erpnext.get_default_cost_center(company)

	return {"account": data.get("account"), "cost_center": cost_center}


@frappe.whitelist()
def get_expense_claim_account(expense_claim_type: str, company: str) -> dict:
	account = frappe.db.get_value(
		"Expense Claim Account", {"parent": expense_claim_type, "company": company}, "default_account"
	)
	if not account:
		frappe.throw(
			_("Set the default account for the {0} {1}").format(
				frappe.bold(_("Expense Claim Type")),
				get_link_to_form("Expense Claim Type", expense_claim_type),
			)
		)

	return {"account": account}


@frappe.whitelist()
def get_advances(expense_claim: str | dict | Document, advance_id: str | None = None):
	import json

	if isinstance(expense_claim, str):
		expense_claim = frappe._dict(json.loads(expense_claim))
	expense_claim_doc = frappe.get_doc(expense_claim)
	frappe.has_permission("Employee", "read", expense_claim_doc.employee, throw=True)
	expense_claim_doc.advances = []

	advance = frappe.qb.DocType("Employee Advance")

	query = frappe.qb.from_(advance).select(
		advance.name,
		advance.purpose,
		advance.posting_date,
		advance.paid_amount,
		advance.claimed_amount,
		advance.return_amount,
		advance.advance_account,
	)

	if not advance_id:
		query = query.where(
			(advance.docstatus == 1)
			& (advance.employee == expense_claim_doc.employee)
			& (advance.paid_amount > 0)
			& (advance.status.notin(["Claimed", "Returned", "Partly Claimed and Returned"]))
		)
	else:
		query = query.where((advance.name == advance_id) & (advance.employee == expense_claim_doc.employee))

	# advance can only be adjusted in its own currency
	if expense_claim_doc.currency:
		query = query.where(advance.currency == expense_claim_doc.currency)

	advances = query.run(as_dict=True)

	for advance in advances:
		get_expense_claim_advances(expense_claim_doc, advance)
	return expense_claim_doc.advances


@frappe.whitelist()
def get_expense_claim(employee_advance: str | dict) -> Document:
	frappe.has_permission("Employee Advance", "read", employee_advance, throw=True)
	if isinstance(employee_advance, str):
		employee_advance = frappe.get_doc("Employee Advance", employee_advance)

	company = employee_advance.company
	default_payable_account = frappe.get_cached_value(
		"Company", company, "default_expense_claim_payable_account"
	)
	default_cost_center = frappe.get_cached_value("Company", company, "cost_center")

	expense_claim = frappe.new_doc("Expense Claim")
	expense_claim.company = company
	expense_claim.currency = employee_advance.currency
	expense_claim.employee = employee_advance.employee
	expense_claim.payable_account = (
		default_payable_account
		if employee_advance.currency == erpnext.get_company_currency(company)
		else None
	)
	expense_claim.cost_center = default_cost_center
	expense_claim.is_paid = 1 if flt(employee_advance.paid_amount) else 0
	get_expense_claim_advances(expense_claim, employee_advance)
	return expense_claim


def get_expense_claim_advances(expense_claim, employee_advance):
	advance_payments = frappe.get_all(
		"Advance Payment Ledger Entry",
		filters={
			"company": expense_claim.company,
			"against_voucher_type": "Employee Advance",
			"against_voucher_no": employee_advance.name,
			"event": "Submit",
			"delinked": False,
			"amount": [">", 0],
		},
		fields=["voucher_type", "voucher_no", "amount", "base_amount", "exchange_rate", "creation"],
	)

	if not advance_payments:
		return

	advance_payments.sort(key=lambda x: x.get("creation"))
	advance_payment_voucher_nos = [payment["voucher_no"] for payment in advance_payments]

	claimed_payments = frappe.get_all(
		"Advance Payment Ledger Entry",
		filters={
			"company": expense_claim.company,
			"event": "Adjustment",
			"against_voucher_no": ["in", advance_payment_voucher_nos],
			"delinked": False,
		},
		fields=[
			"against_voucher_type",
			"against_voucher_no",
			"amount",
		],
	)

	adjustment_map = {}
	for adjustment_entry in claimed_payments:
		payment_reference = (adjustment_entry["against_voucher_type"], adjustment_entry["against_voucher_no"])
		adjustment_map[payment_reference] = adjustment_map.get(payment_reference, 0) + abs(
			adjustment_entry["amount"]
		)

	for advance in advance_payments:
		paid_amount = flt(advance["amount"])
		claimed_amount = adjustment_map.get((advance["voucher_type"], advance["voucher_no"]), 0)
		unclaimed_amount = paid_amount - claimed_amount
		return_amount = flt(employee_advance.return_amount)
		allocated_amount = get_allocation_amount(
			paid_amount=paid_amount, claimed_amount=claimed_amount, return_amount=return_amount
		)

		expense_claim.append(
			"advances",
			{
				"advance_account": employee_advance.advance_account,
				"employee_advance": employee_advance.name,
				"posting_date": employee_advance.posting_date,
				"advance_paid": paid_amount,
				"base_advance_paid": flt(advance["base_amount"]),
				"unclaimed_amount": unclaimed_amount,
				"allocated_amount": allocated_amount,
				"return_amount": return_amount,
				"exchange_rate": advance["exchange_rate"],
				"reference_type": advance["voucher_type"],
				"reference_name": advance["voucher_no"],
			},
		)


def update_payment_for_expense_claim(doc, method=None):
	"""
	Updates payment/reimbursed amount in Expense Claim
	on Payment Entry/Journal Entry cancellation/submission
	"""
	if doc.doctype == "Payment Entry" and not (doc.payment_type == "Pay" and doc.party):
		return

	doctype_field_map = {
		"Journal Entry": ["accounts", "reference_type"],
		"Payment Entry": ["references", "reference_doctype"],
		"Unreconcile Payment": ["allocations", "reference_doctype"],
	}

	payment_table, doctype_field = doctype_field_map[doc.doctype]

	for d in doc.get(payment_table):
		if d.get(doctype_field) == "Expense Claim" and d.reference_name:
			expense_claim = frappe.get_doc("Expense Claim", d.reference_name)
			update_reimbursed_amount(expense_claim)

			if doc.doctype == "Payment Entry":
				update_outstanding_amount_in_payment_entry(expense_claim, d.name)


def update_outstanding_amount_in_payment_entry(expense_claim: dict, pe_reference: str):
	"""updates outstanding amount back in Payment Entry reference"""
	# TODO: refactor convoluted code after erpnext payment entry becomes extensible
	outstanding_amount = get_outstanding_amount_for_claim(expense_claim)
	frappe.db.set_value("Payment Entry Reference", pe_reference, "outstanding_amount", outstanding_amount)


def validate_expense_claim_in_jv(doc, method=None):
	"""Validates Expense Claim amount in Journal Entry"""
	if doc.voucher_type == "Exchange Gain Or Loss":
		return

	for d in doc.accounts:
		if d.reference_type == "Expense Claim":
			outstanding_amt = get_outstanding_amount_for_claim(d.reference_name)
			if d.debit and (d.debit > outstanding_amt):
				frappe.throw(
					_(
						"Row No {0}: Amount cannot be greater than the Outstanding Amount against Expense Claim {1}. Outstanding Amount is {2}"
					).format(d.idx, d.reference_name, outstanding_amt)
				)


@frappe.whitelist()
def make_expense_claim_for_delivery_trip(
	source_name: str, target_doc: str | Document | None = None
) -> Document:
	doc = get_mapped_doc(
		"Delivery Trip",
		source_name,
		{"Delivery Trip": {"doctype": "Expense Claim", "field_map": {"name": "delivery_trip"}}},
		target_doc,
	)

	return doc


@frappe.whitelist()
def get_allocation_amount(
	paid_amount: str | float | None = None,
	claimed_amount: str | float | None = None,
	return_amount: str | float | None = None,
	unclaimed_amount: str | float | None = None,
) -> float | None:
	if unclaimed_amount is not None and return_amount is not None:
		return flt(unclaimed_amount) - flt(return_amount)
	elif paid_amount is not None and claimed_amount is not None and return_amount is not None:
		return flt(paid_amount) - (flt(claimed_amount) + flt(return_amount))
	else:
		frappe.throw(_("Invalid parameters provided. Please pass the required arguments."))
