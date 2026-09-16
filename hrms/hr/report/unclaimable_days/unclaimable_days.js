// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

// Read-only. The rows come from hrms/utils/attendance_recovery.py's detectors;
// nothing on this page writes. Today is never read (the server clips to yesterday).
//
// "Fix" is an ENTRY POINT and nothing more: it opens the Fix Day screen
// (hrms/public/js/fix_day.bundle.js) for the ticked row's employee-day. Every
// correction and every guard lives there and in hrms.api.attendance_fix_day;
// this report still computes nothing and writes nothing itself.
const UD_HR_ROLES = ["HR User", "HR Manager", "System Manager"];

function ud_hr() {
	return UD_HR_ROLES.some((role) => frappe.user.has_role(role));
}

function ud_fix(report) {
	const rows = (report.get_checked_items && report.get_checked_items()) || [];
	const day = rows.length === 1 ? rows[0] : null;
	if (!day || !day.employee || !day.date) {
		frappe.msgprint(__("Tick exactly one row to fix."));
		return;
	}
	console.info("[UnclaimableDays] fix", day.employee, day.date);
	frappe.require("fix_day.bundle.js", () => {
		hrms.fix_day.open({
			employee: day.employee,
			date: day.date,
			on_close: () => report.refresh(),
		});
	});
}

frappe.query_reports["Unclaimable Days"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			// attendance_recovery.REPAIR_FLOOR: OT stays claimable four cycles back.
			default: "2026-08-01",
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "family",
			label: __("Family"),
			fieldtype: "Select",
			options: ["", "F1", "F2", "F4", "F6", "F7", "F9", "F13"],
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: ["", "fixable", "on purpose", "needs HR"],
		},
	],

	onload(report) {
		if (ud_hr()) report.page.add_inner_button(__("Fix"), () => ud_fix(report));
	},

	get_datatable_options(options) {
		return ud_hr() ? Object.assign(options, { checkboxColumn: true }) : options;
	},

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "status" && data) {
			const colour = { fixable: "green", "on purpose": "grey", "needs HR": "orange" }[data.status];
			if (colour) {
				value = `<span class="indicator-pill ${colour}">${frappe.utils.escape_html(
					data.status
				)}</span>`;
			}
		}
		return value;
	},
};
