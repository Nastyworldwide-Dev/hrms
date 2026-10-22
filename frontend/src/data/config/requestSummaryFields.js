// This config holds the fields that should be shown in the request summary action sheet
// TODO: This should be config-driven somehow

export const LEAVE_FIELDS = [
	{
		fieldname: "leave_type",
		label: "Leave Type",
		fieldtype: "Link",
	},
	{
		fieldname: "leave_dates",
		label: "Leave Dates",
		fieldtype: "Data",
	},
	{
		fieldname: "half_day",
		label: "Half Day",
		fieldtype: "Check",
	},
	{
		fieldname: "half_day_session",
		label: "Which half",
		fieldtype: "Data",
	},
	{
		fieldname: "half_day_date",
		label: "Half Day Date",
		fieldtype: "Date",
	},
	{
		fieldname: "total_leave_days",
		label: "Total Leave Days",
		fieldtype: "Float",
	},
	{
		fieldname: "employee",
		label: "Employee",
		fieldtype: "Link",
	},
	{
		fieldname: "leave_balance",
		label: "Leave Balance",
		fieldtype: "Float",
	},
	{
		fieldname: "status",
		label: "Status",
		fieldtype: "Select",
	},
	{
		fieldname: "description",
		label: "Reason",
		fieldtype: "Small Text",
	},
]

//: Who, what, how much, and ONE status (alpha.6 screen journey, 24 Sep 2026).
//: The sheet listed Posting Date, five totals (taxes and advances are always 0
//: here; advances are hidden by owner ruling 15 Sep) and both the document
//: status ("Draft") and the decision ("Waiting").
export const EXPENSE_CLAIM_FIELDS = [
	{
		fieldname: "employee",
		label: "Employee",
		fieldtype: "Link",
	},
	{
		fieldname: "expenses",
		label: "Expenses",
		fieldtype: "Table",
		componentName: "ExpenseItems",
	},
	{
		fieldname: "total_claimed_amount",
		label: "Total",
		fieldtype: "Currency",
	},
	{
		fieldname: "approval_status",
		label: "Status",
		fieldtype: "Select",
	},
]

export const ATTENDANCE_REQUEST_FIELDS = [
	{
		fieldname: "attendance_dates",
		label: "Attendance Dates",
		fieldtype: "Data",
	},
	{
		fieldname: "total_attendance_days",
		label: "Total Attendance Days",
		fieldtype: "Data",
	},
	{
		fieldname: "include_holidays",
		label: "Include Holidays",
		fieldtype: "Check",
	},
	{
		fieldname: "shift",
		label: "Shift",
		fieldtype: "Link",
	},
	{
		fieldname: "reason",
		label: "Reason",
		fieldtype: "Select",
	},
	{
		fieldname: "employee",
		label: "Employee",
		fieldtype: "Link",
	},
]

export const SHIFT_FIELDS = [
	{
		fieldname: "shift_type",
		label: "Shift Type",
		fieldtype: "Link",
	},
	{
		fieldname: "shift_timing",
		label: "Shift Timing",
		fieldtype: "Data",
	},
	{
		fieldname: "shift_dates",
		label: "Shift Dates",
		fieldtype: "Data",
	},
	{
		fieldname: "total_shift_days",
		label: "Total Shift Days",
		fieldtype: "Data",
	},
	{
		fieldname: "employee",
		label: "Employee",
		fieldtype: "Link",
	},
]

export const SHIFT_REQUEST_FIELDS = [
	{
		fieldname: "shift_type",
		label: "Shift Type",
		fieldtype: "Link",
	},
	{
		fieldname: "shift_dates",
		label: "Shift Dates",
		fieldtype: "Data",
	},
	{
		fieldname: "total_shift_days",
		label: "Total Shift Days",
		fieldtype: "Data",
	},
	{
		fieldname: "employee",
		label: "Employee",
		fieldtype: "Link",
	},
	{
		fieldname: "status",
		label: "Status",
		fieldtype: "Select",
	},
]

export const OT_REQUEST_FIELDS = [
	{
		fieldname: "employee",
		label: "Employee",
		fieldtype: "Link",
	},
	{
		fieldname: "ot_date",
		label: "OT Date",
		fieldtype: "Date",
	},
	{
		fieldname: "shift",
		label: "Shift",
		fieldtype: "Link",
	},
	{
		fieldname: "punch_ot_hours",
		label: "Hours From Punches",
		fieldtype: "Float",
	},
	{
		fieldname: "claimed_hours",
		label: "Claimed Hours",
		fieldtype: "Float",
	},
	{
		fieldname: "compensation",
		label: "Compensation",
		fieldtype: "Select",
	},
	{
		fieldname: "status",
		label: "Status",
		fieldtype: "Select",
	},
	{
		fieldname: "explanation",
		label: "Explanation",
		fieldtype: "Small Text",
	},
]

export const REPLACEMENT_LEAVE_CLAIM_FIELDS = [
	{
		fieldname: "employee",
		label: "Employee",
		fieldtype: "Link",
	},
	{
		fieldname: "bank_month",
		label: "Bank Month",
		fieldtype: "Date",
	},
	{
		fieldname: "claimed_days",
		label: "Claimed Days",
		fieldtype: "Float",
	},
	{
		fieldname: "hours_cost",
		label: "Hours Used",
		fieldtype: "Float",
	},
	{
		fieldname: "available_hours",
		label: "Hours Available",
		fieldtype: "Float",
	},
	{
		fieldname: "status",
		label: "Status",
		fieldtype: "Select",
	},
	{
		fieldname: "explanation",
		label: "Explanation",
		fieldtype: "Small Text",
	},
]

const COMPENSATORY_LEAVE_REQUEST_FIELDS = [
	{
		fieldname: "employee",
		label: "Employee",
		fieldtype: "Link",
	},
	{
		fieldname: "leave_type",
		label: "Leave Type",
		fieldtype: "Link",
	},
	{
		fieldname: "work_from_date",
		label: "Work From Date",
		fieldtype: "Date",
	},
	{
		fieldname: "work_end_date",
		label: "Work End Date",
		fieldtype: "Date",
	},
	{
		fieldname: "half_day",
		label: "Half Day",
		fieldtype: "Check",
	},
	{
		fieldname: "status",
		label: "Status",
		fieldtype: "Select",
	},
	{
		fieldname: "reason",
		label: "Reason",
		fieldtype: "Small Text",
	},
]

//: What an approver decides on: who, what, how many, how soon, the pay (the mockup's approver sheet).
//: The one-line "Driver ×3 · Ops" heads it (utils/manpowerRequest.js summaryLine).
export const MANPOWER_REQUEST_FIELDS = [
	{ fieldname: "employee", label: "From", fieldtype: "Link" },
	{ fieldname: "position_title", label: "Position", fieldtype: "Data" },
	{ fieldname: "headcount", label: "People needed", fieldtype: "Int" },
	{ fieldname: "department", label: "Department", fieldtype: "Link" },
	{ fieldname: "request_type", label: "This is", fieldtype: "Select" },
	{ fieldname: "how_soon", label: "How soon", fieldtype: "Select" },
	{ fieldname: "band", label: "Band", fieldtype: "Select" },
	{ fieldname: "proposed_salary", label: "Proposed Salary", fieldtype: "Currency" },
	{ fieldname: "budgeted_salary", label: "Budgeted Salary", fieldtype: "Currency" },
	{ fieldname: "start_date", label: "Start Date", fieldtype: "Date" },
	{ fieldname: "justification", label: "Reason", fieldtype: "Small Text" },
]

// Summary fields by doctype — what RequestActionSheet renders above its
// Approve / Reject bar. Shared so a form can open the same sheet the Team
// Requests list opens, instead of growing a second approval path.
export const REQUEST_SUMMARY_FIELDS = {
	"Leave Application": LEAVE_FIELDS,
	"Expense Claim": EXPENSE_CLAIM_FIELDS,
	"Attendance Request": ATTENDANCE_REQUEST_FIELDS,
	"Shift Request": SHIFT_REQUEST_FIELDS,
	"OT Request": OT_REQUEST_FIELDS,
	"Replacement Leave Claim": REPLACEMENT_LEAVE_CLAIM_FIELDS,
	"Compensatory Leave Request": COMPENSATORY_LEAVE_REQUEST_FIELDS,
	"Manpower Request": MANPOWER_REQUEST_FIELDS,
}
