// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

// Read-only. The rows come from hrms/utils/attendance_recovery.py's detectors;
// nothing on this page writes. Today is never read (the server clips to yesterday).
//
// "Punches" is a LINK and nothing more: it opens the Employee Checkin list on
// the ticked row's employee-day, the only page that carries the Fix Day tools
// (owner, 21 Sep 2026). Every correction and every guard lives there and in
// hrms.api.attendance_fix_day; this report computes nothing and writes nothing.
const UD_HR_ROLES = ["HR User", "HR Manager", "System Manager"];

function ud_hr() {
	return UD_HR_ROLES.some((role) => frappe.user.has_role(role));
}

function ud_punches(report) {
	const rows = (report.get_checked_items && report.get_checked_items()) || [];
	const day = rows.length === 1 ? rows[0] : null;
	if (!day || !day.employee || !day.date) {
		frappe.msgprint(__("Tick exactly one row."));
		return;
	}
	console.info("[UnclaimableDays] punches", day.employee, day.date);
	frappe.set_route("List", "Employee Checkin", {
		employee: day.employee,
		time: ["Between", [day.date, day.date]],
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
		if (ud_hr()) report.page.add_inner_button(__("Punches"), () => ud_punches(report));
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
