app_name = "hrms"
app_title = "Nadi"
app_publisher = "Frappe Technologies Pvt. Ltd."
app_description = "Modern HR and Payroll Software"
app_email = "contact@frappe.io"
app_license = "GNU General Public License (v3)"
required_apps = ["frappe/erpnext"]
source_link = "http://github.com/frappe/hrms"
app_logo_url = "/assets/hrms/images/nadi-logo.png"
app_home = "/desk/people"

add_to_apps_screen = [
	{
		"name": "hrms",
		"logo": "/assets/hrms/images/nadi-logo.png",
		"title": "Nadi",
		"route": "/desk/people",
		"has_permission": "hrms.hr.utils.check_app_permission",
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/hrms/css/hrms.css"
app_include_js = [
	"hrms.bundle.js",
]
app_include_css = "hrms.bundle.css"

# website

# include js, css files in header of web template
# web_include_css = "/assets/hrms/css/hrms.css"
# web_include_js = "/assets/hrms/js/hrms.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "hrms/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Employee": "public/js/erpnext/employee.js",
	"Company": "public/js/erpnext/company.js",
	"Department": "public/js/erpnext/department.js",
	"Timesheet": "public/js/erpnext/timesheet.js",
	"Payment Entry": "public/js/erpnext/payment_entry.js",
	"Journal Entry": "public/js/erpnext/journal_entry.js",
	"Delivery Trip": "public/js/erpnext/delivery_trip.js",
	"Bank Transaction": "public/js/erpnext/bank_transaction.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

calendars = ["Leave Application"]

# Generators
# ----------

# automatically create page for each record of this doctype
website_generators = ["Job Opening"]

website_route_rules = [
	{"from_route": "/hrms/<path:app_path>", "to_route": "hrms"},
	{"from_route": "/hr/<path:app_path>", "to_route": "roster"},
]
# Jinja
# ----------

# add methods and filters to jinja environment
#
# `hrms.utils.get_country` was registered here and is not called by any template
# in this app. Registering it was the only thing keeping it reachable, and it is
# a poor thing to keep reachable: `@frappe.whitelist(allow_guest=True)`, an
# outbound request to pro.ip-api.com with NO timeout, and a module-global dict
# keyed by request IP that is never bounded. Unauthenticated callers could grow
# a worker's memory without limit, and one hung upstream pins that worker
# indefinitely. `hrms/sync/client.py` is the same shape done correctly, with an
# explicit timeout and bounded retries.
#
# The function is left in place for upstream-merge parity; only the reachability
# is removed.
jinja = {}

# Installation
# ------------

# before_install = "hrms.install.before_install"
after_install = "hrms.install.after_install"
after_migrate = "hrms.setup.update_select_perm_after_install"

setup_wizard_complete = "hrms.subscription_utils.update_erpnext_access"

# Uninstallation
# ------------

before_uninstall = "hrms.uninstall.before_uninstall"
# after_uninstall = "hrms.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "hrms.utils.before_app_install"
after_app_install = "hrms.setup.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

before_app_uninstall = "hrms.setup.before_app_uninstall"
# after_app_uninstall = "hrms.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "hrms.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

permission_query_conditions = {
	# Employees may only see their own Appraisal; HR User/Manager and
	# System Manager keep full visibility for the rating workflow.
	"Appraisal": "hrms.hr.doctype.appraisal.appraisal.get_permission_query_conditions",
	# Scope notification reads to the recipient. Doctype-level perms only grant
	# read to Employee + System Manager; HR Managers acting as approvers would
	# otherwise see an empty feed even when their unread count is nonzero.
	"PWA Notification": "hrms.hr.doctype.pwa_notification.pwa_notification.get_permission_query_conditions",
	# Participants only: both doctypes carry Employee Link fields that ignore
	# user permissions, so row scope lives entirely in these hooks.
	"Employee One On One": "hrms.hr.doctype.employee_one_on_one.employee_one_on_one.get_permission_query_conditions",
	"Employee Instant Feedback": "hrms.hr.doctype.employee_instant_feedback.employee_instant_feedback.get_permission_query_conditions",
	"Shift Swap Request": "hrms.hr.doctype.shift_swap_request.shift_swap_request.get_permission_query_conditions",
	# Approver-routed requests: own + named approver + shared + HR. Row scope
	# lives here, NOT in per-employee User Permissions (which would 403 the
	# approver) — see hrms/overrides/approval_row_scope.py.
	"Leave Application": "hrms.overrides.approval_row_scope.leave_application_query_conditions",
	# OT money-flow doctypes: own + direct reports + HR (no approver field —
	# submission is the approval)
	"OT Request": "hrms.overrides.ot_row_scope.ot_request_query_conditions",
	"Replacement Leave Claim": "hrms.overrides.ot_row_scope.replacement_leave_claim_query_conditions",
	"Expense Claim": "hrms.overrides.approval_row_scope.expense_claim_query_conditions",
	"Shift Request": "hrms.overrides.approval_row_scope.shift_request_query_conditions",
	# Helpdesk tickets: private employee↔HR, no reports_to visibility
	"Employee Issue": "hrms.overrides.employee_issue_row_scope.get_permission_query_conditions",
	# SOP Library: published General SOPs + the reader's own department; HR sees all
	"SOP Document": "hrms.overrides.sop_document_row_scope.get_permission_query_conditions",
	# Multi-company hub: a user carrying an allow=Company User Permission
	# ("HR (Company)") never sees another company's Employee. No-op for users
	# without one — see hrms/overrides/company_scope.py.
	"Employee": "hrms.overrides.company_scope.employee_query_conditions",
	# ---- Employee-owned HR records -------------------------------------
	# Each of these grants the Employee/ESS role level-0 rights, so without a
	# hook the grant means "every employee's rows" — pay, benefits, promotions,
	# attendance, check-ins — through Desk, /api/resource, report view and CSV
	# export. Scope is own + DocShare, with HR broad INSIDE its company fence.
	# Listed literally so a reviewer can see the whole boundary in one place;
	# tests/test_employee_role_fence_integrity.py fails if one goes missing or
	# is wired on only one of the two hooks.
	# See hrms/overrides/employee_owned_row_scope.py.
	"Attendance": "hrms.overrides.employee_owned_row_scope.query_attendance",
	"Attendance Request": "hrms.overrides.employee_owned_row_scope.query_attendance_request",
	"Compensatory Leave Request": "hrms.overrides.employee_owned_row_scope.query_compensatory_leave_request",
	"Employee Checkin": "hrms.overrides.employee_owned_row_scope.query_employee_checkin",
	"Remote Checkin Request": "hrms.overrides.employee_owned_row_scope.query_remote_checkin_request",
	"Shift Assignment": "hrms.overrides.employee_owned_row_scope.query_shift_assignment",
	"Shift Schedule Assignment": "hrms.overrides.employee_owned_row_scope.query_shift_schedule_assignment",
	"Employee Advance": "hrms.overrides.employee_owned_row_scope.query_employee_advance",
	"Employee Benefit Application": "hrms.overrides.employee_owned_row_scope.query_employee_benefit_application",
	"Employee Benefit Claim": "hrms.overrides.employee_owned_row_scope.query_employee_benefit_claim",
	"Employee Benefit Ledger": "hrms.overrides.employee_owned_row_scope.query_employee_benefit_ledger",
	"Employee Incentive": "hrms.overrides.employee_owned_row_scope.query_employee_incentive",
	"Employee Other Income": "hrms.overrides.employee_owned_row_scope.query_employee_other_income",
	"Employee Tax Exemption Declaration": "hrms.overrides.employee_owned_row_scope.query_employee_tax_exemption_declaration",
	"Employee Tax Exemption Proof Submission": "hrms.overrides.employee_owned_row_scope.query_employee_tax_exemption_proof_submission",
	"Leave Encashment": "hrms.overrides.employee_owned_row_scope.query_leave_encashment",
	"Overtime Slip": "hrms.overrides.employee_owned_row_scope.query_overtime_slip",
	"Payroll Correction": "hrms.overrides.employee_owned_row_scope.query_payroll_correction",
	"Retention Bonus": "hrms.overrides.employee_owned_row_scope.query_retention_bonus",
	"Salary Structure Assignment": "hrms.overrides.employee_owned_row_scope.query_salary_structure_assignment",
	"Salary Withholding": "hrms.overrides.employee_owned_row_scope.query_salary_withholding",
	"Employee Transfer": "hrms.overrides.employee_owned_row_scope.query_employee_transfer",
	"Employee Promotion": "hrms.overrides.employee_owned_row_scope.query_employee_promotion",
	"Employee Performance Feedback": "hrms.overrides.employee_owned_row_scope.query_employee_performance_feedback",
	"Performance Improvement Plan": "hrms.overrides.employee_owned_row_scope.query_performance_improvement_plan",
	"Goal": "hrms.overrides.employee_owned_row_scope.query_goal",
	"Training Feedback": "hrms.overrides.employee_owned_row_scope.query_training_feedback",
	"Employee Referral": "hrms.overrides.employee_owned_row_scope.query_employee_referral",
	"Employee Grievance": "hrms.overrides.employee_owned_row_scope.query_employee_grievance",
}

has_permission = {
	"Appraisal": "hrms.hr.doctype.appraisal.appraisal.has_permission",
	"PWA Notification": "hrms.hr.doctype.pwa_notification.pwa_notification.has_permission",
	"Employee One On One": "hrms.hr.doctype.employee_one_on_one.employee_one_on_one.has_permission",
	"Employee Instant Feedback": "hrms.hr.doctype.employee_instant_feedback.employee_instant_feedback.has_permission",
	"Shift Swap Request": "hrms.hr.doctype.shift_swap_request.shift_swap_request.has_permission",
	"Leave Application": "hrms.overrides.approval_row_scope.has_permission",
	"Expense Claim": "hrms.overrides.approval_row_scope.has_permission",
	"Shift Request": "hrms.overrides.approval_row_scope.has_permission",
	"OT Request": "hrms.overrides.ot_row_scope.has_permission",
	"Replacement Leave Claim": "hrms.overrides.ot_row_scope.has_permission",
	"Employee Issue": "hrms.overrides.employee_issue_row_scope.has_permission",
	"SOP Document": "hrms.overrides.sop_document_row_scope.has_permission",
	"Employee": "hrms.overrides.company_scope.employee_has_permission",
	# Document-level twin of the query scope above. A query condition filters
	# list views only — frappe.client.get, form loads, print/PDF and attachment
	# fetches all route through has_permission, so both must be wired or the
	# doctype is only half-fenced.
	"Attendance": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Attendance Request": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Compensatory Leave Request": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Employee Checkin": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Remote Checkin Request": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Shift Assignment": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Shift Schedule Assignment": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Employee Advance": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Employee Benefit Application": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Employee Benefit Claim": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Employee Benefit Ledger": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Employee Incentive": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Employee Other Income": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Employee Tax Exemption Declaration": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Employee Tax Exemption Proof Submission": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Leave Encashment": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Overtime Slip": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Payroll Correction": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Retention Bonus": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Salary Structure Assignment": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Salary Withholding": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Employee Transfer": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Employee Promotion": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Employee Performance Feedback": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Performance Improvement Plan": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Goal": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Training Feedback": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Employee Referral": "hrms.overrides.employee_owned_row_scope.has_permission",
	"Employee Grievance": "hrms.overrides.employee_owned_row_scope.has_permission",
}

has_upload_permission = {"Employee": "erpnext.setup.doctype.employee.employee.has_upload_permission"}

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Employee": "hrms.overrides.employee_master.EmployeeMaster",
	"Timesheet": "hrms.overrides.employee_timesheet.EmployeeTimesheet",
	"Payment Entry": "hrms.overrides.employee_payment_entry.EmployeePaymentEntry",
	"Project": "hrms.overrides.employee_project.EmployeeProject",
	"Employee Checkin": "hrms.overrides.employee_checkin_override.CustomEmployeeCheckin",
	"Leave Policy Assignment": "hrms.overrides.leave_policy_assignment_override.CustomLeavePolicyAssignment",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"User": {
		"validate": [
			"erpnext.setup.doctype.employee.employee.validate_employee_role",
			"hrms.overrides.employee_master.update_approver_user_roles",
		],
	},
	"DocShare": {
		# manual appraisal grants stay per-user and non-transferable
		"validate": "hrms.hr.doctype.appraisal.appraisal.validate_appraisal_doc_share",
	},
	"Company": {
		"validate": "hrms.overrides.company.validate_default_accounts",
		"on_update": [
			"hrms.overrides.company.make_company_fixtures",
			"hrms.overrides.company.set_default_hr_accounts",
		],
		"on_trash": "hrms.overrides.company.handle_linked_docs",
	},
	"Holiday List": {
		"on_update": "hrms.utils.holiday_list.invalidate_cache",
		"on_trash": "hrms.utils.holiday_list.invalidate_cache",
	},
	"Timesheet": {"validate": "hrms.hr.utils.validate_active_employee"},
	"Payment Entry": {
		"on_submit": "hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
		"on_cancel": "hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
		"on_update_after_submit": "hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
	},
	"Unreconcile Payment": {
		"on_submit": "hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
	},
	"Journal Entry": {
		"validate": "hrms.hr.doctype.expense_claim.expense_claim.validate_expense_claim_in_jv",
		"on_submit": [
			"hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
			"hrms.hr.doctype.full_and_final_statement.full_and_final_statement.update_full_and_final_statement_status",
			"hrms.payroll.doctype.salary_withholding.salary_withholding.update_salary_withholding_payment_status",
		],
		"on_update_after_submit": "hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
		"on_cancel": [
			"hrms.hr.doctype.expense_claim.expense_claim.update_payment_for_expense_claim",
			"hrms.payroll.doctype.salary_slip.salary_slip.unlink_ref_doc_from_salary_slip",
			"hrms.hr.doctype.full_and_final_statement.full_and_final_statement.update_full_and_final_statement_status",
			"hrms.payroll.doctype.salary_withholding.salary_withholding.update_salary_withholding_payment_status",
		],
	},
	"Loan": {"validate": "hrms.hr.utils.validate_loan_repay_from_salary"},
	"Employee": {
		"validate": [
			# First on purpose: a mirrored row must be rejected before any other
			# validate handler runs side effects (single-writer, see write_block).
			"hrms.sync.write_block.block_mirrored_writes",
			"hrms.overrides.employee_master.validate_onboarding_process",
			"hrms.overrides.employee_interco_allocation.validate_interco_allocation",
			"hrms.overrides.employee_master.set_years_of_service",
		],
		"on_update": [
			"hrms.overrides.employee_master.update_approver_role",
			"hrms.overrides.employee_master.publish_update",
			# Reconcile the rule-managed Shift Assignment when shift_location /
			# department changes (no-op otherwise; never blocks the save).
			"hrms.hr.shift_rules.reconcile_on_employee_update",
			# Runs LAST on purpose: ERPNext's Employee.on_update controller method
			# fires before this hook and may delete any `allow=Employee` User
			# Permissions when `create_user_permission` is unticked. Running our
			# handler in after_save (the previous wiring) meant ERPNext nuked the
			# 16 scoped UPs we just inserted. Hooking to on_update runs us AFTER
			# the controller, so the UPs survive.
			"hrms.overrides.employee_hrms_scope.sync_hrms_only_user_permission",
		],
		"after_insert": [
			"hrms.overrides.employee_master.update_job_applicant_and_offer",
			"hrms.telemetry.on_milestone_insert",
		],
		"on_trash": [
			"hrms.sync.write_block.block_mirrored_writes",
			"hrms.overrides.employee_master.update_employee_transfer",
		],
		# rename_doc fires before_rename, never validate — without this hook a
		# rename bypasses the guard and breaks the name-keyed mirror (SEC-01).
		"before_rename": "hrms.sync.write_block.block_mirrored_writes",
		"after_delete": "hrms.overrides.employee_master.publish_update",
	},
	# ONE entry per doctype: a duplicate key in this dict literal silently
	# drops the earlier one — a second "Employee Checkin" key did exactly that
	# to the out-of-radius handler in the v16 port (test_write_block pins it).
	"Employee Checkin": {
		"validate": "hrms.sync.write_block.block_mirrored_writes",
		"after_insert": [
			"hrms.overrides.employee_checkin_after_insert.create_remote_request_if_needed",
			"hrms.telemetry.on_employee_checkin",
		],
		"on_trash": "hrms.sync.write_block.block_mirrored_writes",
		"before_rename": "hrms.sync.write_block.block_mirrored_writes",
	},
	# Mirrored during the parallel run (hrms/sync/runner.py): every write path
	# — edit, update-after-submit, cancel, delete, rename — runs the guard.
	"Attendance": {
		"validate": "hrms.sync.write_block.block_mirrored_writes",
		"before_update_after_submit": "hrms.sync.write_block.block_mirrored_writes",
		"before_cancel": "hrms.sync.write_block.block_mirrored_writes",
		"on_trash": "hrms.sync.write_block.block_mirrored_writes",
		"before_rename": "hrms.sync.write_block.block_mirrored_writes",
	},
	"Leave Ledger Entry": {
		"validate": "hrms.sync.write_block.block_mirrored_writes",
		"before_update_after_submit": "hrms.sync.write_block.block_mirrored_writes",
		"before_cancel": "hrms.sync.write_block.block_mirrored_writes",
		"on_trash": "hrms.sync.write_block.block_mirrored_writes",
		"before_rename": "hrms.sync.write_block.block_mirrored_writes",
	},
	# Mirrored from 2026-08-19; same guard set as Attendance. The appraisal
	# masters (KRA, Appraisal Template, Appraisal Cycle) stay unguarded —
	# create-only, HR-owned here.
	"Appraisal": {
		"validate": "hrms.sync.write_block.block_mirrored_writes",
		"before_update_after_submit": "hrms.sync.write_block.block_mirrored_writes",
		"before_cancel": "hrms.sync.write_block.block_mirrored_writes",
		"on_trash": "hrms.sync.write_block.block_mirrored_writes",
		"before_rename": "hrms.sync.write_block.block_mirrored_writes",
	},
	# Holiday policy and shift planning. The MASTERS these point at — Holiday List,
	# Shift Type, Shift Schedule — are deliberately NOT guarded: they are mirrored
	# create-only and owned by HR here, so a policy change made on this hub must be
	# allowed and must survive the next run. The per-employee ASSIGNMENTS are the
	# mirror proper, and a policy change supersedes one by adding a newer record
	# rather than by editing a mirrored one — which is what keeps parity honest.
	"Shift Assignment": {
		"validate": "hrms.sync.write_block.block_mirrored_writes",
		"before_update_after_submit": "hrms.sync.write_block.block_mirrored_writes",
		"before_cancel": "hrms.sync.write_block.block_mirrored_writes",
		"on_trash": "hrms.sync.write_block.block_mirrored_writes",
		"before_rename": "hrms.sync.write_block.block_mirrored_writes",
	},
	# Not submittable, so it has no update-after-submit or cancel path to guard.
	"Shift Schedule Assignment": {
		"validate": "hrms.sync.write_block.block_mirrored_writes",
		"on_trash": "hrms.sync.write_block.block_mirrored_writes",
		"before_rename": "hrms.sync.write_block.block_mirrored_writes",
	},
	"Remote Checkin Request": {
		"on_update": "hrms.overrides.remote_checkin_request_hooks.propagate_approval_decision",
	},
	"Project": {"validate": "hrms.controllers.employee_boarding_controller.update_employee_boarding_status"},
	"Task": {"on_update": "hrms.controllers.employee_boarding_controller.update_task"},
	# ---- Usage telemetry: recurring feature usage (see hrms/telemetry.py) ----
	# ONE entry per doctype (see the Employee Checkin note above). Leave
	# Application carries both the telemetry hook and the single-writer guard:
	# submit/cancel write Leave Ledger Entry rows, which are mirrored, so a
	# hub-side approval for a mirrored employee would silently diverge from the
	# source and stay invisible to hrms.sync.parity.
	# Leave Application is now MIRRORED as well, so it carries both guards. They
	# answer different questions and neither replaces the other:
	# `block_transactions_for_mirrored_employee` refuses a NEW hub-side transaction
	# for someone the source owns; `block_mirrored_writes` refuses an edit to a row
	# the sync itself wrote. Merged into this one key rather than added as a second
	# — a duplicate doctype key in a dict literal silently drops the earlier entry,
	# which is how the out-of-radius handler was lost in the v16 port.
	"Leave Application": {
		"on_submit": "hrms.telemetry.on_leave_application_submit",
		"before_submit": "hrms.sync.write_block.block_transactions_for_mirrored_employee",
		"validate": "hrms.sync.write_block.block_mirrored_writes",
		"before_update_after_submit": "hrms.sync.write_block.block_mirrored_writes",
		"before_cancel": [
			"hrms.sync.write_block.block_transactions_for_mirrored_employee",
			"hrms.sync.write_block.block_mirrored_writes",
		],
		"on_trash": "hrms.sync.write_block.block_mirrored_writes",
		"before_rename": "hrms.sync.write_block.block_mirrored_writes",
	},
	"Expense Claim": {"on_submit": "hrms.telemetry.on_expense_claim_submit"},
	# Both guards, for the same reason as Leave Application above: the ROW guard
	# refuses edits to a mirrored request, the TRANSACTION guard refuses a NEW
	# hub-side request whose on_submit writes mirrored data (Attendance Request
	# -> Attendance, Shift Request -> Shift Assignment) for an employee the
	# source instance owns.
	"Attendance Request": {
		"on_submit": "hrms.telemetry.on_attendance_request_submit",
		"before_submit": "hrms.sync.write_block.block_transactions_for_mirrored_employee",
		"validate": "hrms.sync.write_block.block_mirrored_writes",
		"before_update_after_submit": "hrms.sync.write_block.block_mirrored_writes",
		"before_cancel": [
			"hrms.sync.write_block.block_transactions_for_mirrored_employee",
			"hrms.sync.write_block.block_mirrored_writes",
		],
		"on_trash": "hrms.sync.write_block.block_mirrored_writes",
		"before_rename": "hrms.sync.write_block.block_mirrored_writes",
	},
	"Shift Request": {
		"on_submit": "hrms.telemetry.on_shift_request_submit",
		"before_submit": "hrms.sync.write_block.block_transactions_for_mirrored_employee",
		"validate": "hrms.sync.write_block.block_mirrored_writes",
		"before_update_after_submit": "hrms.sync.write_block.block_mirrored_writes",
		"before_cancel": [
			"hrms.sync.write_block.block_transactions_for_mirrored_employee",
			"hrms.sync.write_block.block_mirrored_writes",
		],
		"on_trash": "hrms.sync.write_block.block_mirrored_writes",
		"before_rename": "hrms.sync.write_block.block_mirrored_writes",
	},
	# Not mirrored itself (no row guard), but its on_submit adds days to a Leave
	# Allocation and its on_cancel takes them back — mirrored balances either way.
	"Compensatory Leave Request": {
		"before_submit": "hrms.sync.write_block.block_transactions_for_mirrored_employee",
		"before_cancel": "hrms.sync.write_block.block_transactions_for_mirrored_employee",
	},
	"Leave Allocation": {
		"validate": "hrms.sync.write_block.block_mirrored_writes",
		"before_update_after_submit": "hrms.sync.write_block.block_mirrored_writes",
		"before_cancel": "hrms.sync.write_block.block_mirrored_writes",
		"on_trash": "hrms.sync.write_block.block_mirrored_writes",
		"before_rename": "hrms.sync.write_block.block_mirrored_writes",
	},
	"Leave Policy Assignment": {
		"validate": "hrms.sync.write_block.block_mirrored_writes",
		"before_update_after_submit": "hrms.sync.write_block.block_mirrored_writes",
		"before_cancel": "hrms.sync.write_block.block_mirrored_writes",
		"on_trash": "hrms.sync.write_block.block_mirrored_writes",
		"before_rename": "hrms.sync.write_block.block_mirrored_writes",
	},
	# (Employee Checkin telemetry lives in the single entry above — a second
	# key here would silently clobber it.)
	# ---- Activation telemetry: post-install setup funnel (first-time milestones) ----
	"Shift Type": {"after_insert": "hrms.telemetry.on_milestone_insert"},
	"Leave Type": {"after_insert": "hrms.telemetry.on_milestone_insert"},
	"Salary Structure": {"after_insert": "hrms.telemetry.on_milestone_insert"},
	"Job Opening": {"after_insert": "hrms.telemetry.on_milestone_insert"},
	"Appraisal Cycle": {"after_insert": "hrms.telemetry.on_milestone_insert"},
	"Employee Onboarding": {"after_insert": "hrms.telemetry.on_milestone_insert"},
	"Salary Slip": {"on_submit": "hrms.telemetry.on_milestone_submit"},
	"Payroll Entry": {"on_submit": "hrms.telemetry.on_milestone_submit"},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"all": [
		"hrms.hr.doctype.interview.interview.send_interview_reminder",
	],
	"hourly": [
		"hrms.hr.doctype.daily_work_summary_group.daily_work_summary_group.trigger_emails",
	],
	"hourly_long": [
		"hrms.hr.doctype.shift_type.shift_type.update_last_sync_of_checkin",
		"hrms.hr.doctype.shift_type.shift_type.process_auto_attendance_for_all_shifts",
		"hrms.hr.doctype.shift_schedule_assignment.shift_schedule_assignment.process_auto_shift_creation",
	],
	"daily": [
		"hrms.hr.shift_rules.sync_shift_assignments",
		"hrms.hr.leave_rules.auto_assign_leave_policies",
		"hrms.overrides.employee_master.update_all_years_of_service",
		"hrms.controllers.employee_reminders.send_birthday_reminders",
		"hrms.controllers.employee_reminders.send_work_anniversary_reminders",
		"hrms.hr.doctype.daily_work_summary_group.daily_work_summary_group.send_summary",
		"hrms.hr.doctype.interview.interview.send_daily_feedback_reminder",
		"hrms.hr.doctype.shift_assignment.shift_assignment.mark_expired_shift_assignments_as_inactive",
		"hrms.hr.doctype.job_opening.job_opening.close_expired_job_openings",
		"hrms.telemetry.capture_daily_attendance_pulse",
		# Re-reconcile fence-role users against the instance registry and
		# report HR users the fail-open fence default leaves unfenced.
		"hrms.utils.company_fence.nightly_fence_hygiene",
	],
	"cron": {
		# 10:00 local — tag abandoned IN check-ins (no matching OUT within 36h).
		"0 10 * * *": [
			"hrms.utils.checkin_sweeper.sweep_stale_ins",
		],
	},
	"daily_long": [
		"hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry.process_expired_allocation",
		"hrms.hr.utils.generate_leave_encashment",
		"hrms.hr.utils.allocate_earned_leaves",
	],
	"weekly": ["hrms.controllers.employee_reminders.send_reminders_in_advance_weekly"],
	"monthly": ["hrms.controllers.employee_reminders.send_reminders_in_advance_monthly"],
}

advance_payment_payable_doctypes = ["Leave Encashment", "Gratuity", "Employee Advance"]

invoice_doctypes = ["Expense Claim"]

period_closing_doctypes = ["Payroll Entry"]

accounting_dimension_doctypes = [
	"Expense Claim",
	"Expense Claim Detail",
	"Expense Taxes and Charges",
	"Payroll Entry",
	"Leave Encashment",
]

bank_reconciliation_doctypes = ["Expense Claim"]

# Testing
# -------

before_tests = "hrms.tests.test_utils.before_tests"

# Overriding Methods
# -----------------------------

# get matching queries for Bank Reconciliation
get_matching_queries = "hrms.hr.utils.get_matching_queries"

regional_overrides = {
	"India": {
		"hrms.hr.utils.calculate_annual_eligible_hra_exemption": "hrms.regional.india.utils.calculate_annual_eligible_hra_exemption",
		"hrms.hr.utils.calculate_hra_exemption_for_period": "hrms.regional.india.utils.calculate_hra_exemption_for_period",
		"hrms.hr.utils.calculate_tax_with_marginal_relief": "hrms.regional.india.utils.calculate_tax_with_marginal_relief",
	},
}

# ERPNext doctypes for Global Search
global_search_doctypes = {
	"Default": [
		{"doctype": "Salary Slip", "index": 19},
		{"doctype": "Leave Application", "index": 20},
		{"doctype": "Expense Claim", "index": 21},
		{"doctype": "Employee Grade", "index": 37},
		{"doctype": "Job Opening", "index": 39},
		{"doctype": "Job Applicant", "index": 40},
		{"doctype": "Job Offer", "index": 41},
		{"doctype": "Salary Structure Assignment", "index": 42},
		{"doctype": "Appraisal", "index": 43},
	],
}

# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "hrms.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
override_doctype_dashboards = {
	"Employee": "hrms.overrides.dashboard_overrides.get_dashboard_for_employee",
	"Holiday List": "hrms.overrides.dashboard_overrides.get_dashboard_for_holiday_list",
	"Task": "hrms.overrides.dashboard_overrides.get_dashboard_for_project",
	"Project": "hrms.overrides.dashboard_overrides.get_dashboard_for_project",
	"Timesheet": "hrms.overrides.dashboard_overrides.get_dashboard_for_timesheet",
	"Bank Account": "hrms.overrides.dashboard_overrides.get_dashboard_for_bank_account",
}

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

ignore_links_on_delete = ["PWA Notification"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"hrms.auth.validate"
# ]

# Translation
# --------------------------------

# Make link fields search translated document names for these DocTypes
# Recommended only for DocTypes which have limited documents with untranslated names
# For example: Role, Gender, etc.
# translated_search_doctypes = []

company_data_to_be_ignored = [
	"Salary Component Account",
	"Salary Structure",
	"Salary Structure Assignment",
	"Payroll Period",
	"Income Tax Slab",
	"Leave Period",
	"Leave Policy Assignment",
	"Employee Onboarding Template",
	"Employee Separation Template",
]

# List of apps whose translatable strings should be excluded from this app's translations.
ignore_translatable_strings_from = ["frappe", "erpnext"]
employee_holiday_list = ["hrms.utils.holiday_list.get_holiday_list_for_employee"]
export_python_type_annotations = True
require_type_annotated_api_methods = True
repost_allowed_doctypes = ["Expense Claim"]
