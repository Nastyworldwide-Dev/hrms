// Read-only: the days the 16-hour button bug saved a check-out as a second
// check-in (before alpha.10). Each row suggests the check-out; HR confirms it
// on the Employee Checkin list (Fix attendance) — nothing here writes.
// "Punches" is a LINK, the same door the Unclaimable Days report uses.
const MC_HR_ROLES = ["HR User", "HR Manager", "System Manager"];

function mc_hr() {
	return MC_HR_ROLES.some((role) => frappe.user.has_role(role));
}

function mc_punches(report) {
	const rows = (report.get_checked_items && report.get_checked_items()) || [];
	const day = rows.length === 1 ? rows[0] : null;
	if (!day || !day.employee || !day.day) {
		frappe.msgprint(__("Tick exactly one row."));
		return;
	}
	console.info("[MissedCheckouts] punches", day.employee, day.day);
	frappe.set_route("List", "Employee Checkin", {
		employee: day.employee,
		time: ["Between", [day.day, frappe.datetime.add_days(day.day, 1)]],
	});
}

frappe.query_reports["Missed Check-outs After Midnight"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: "2026-08-01", reqd: 1 },
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -1),
			reqd: 1,
		},
		{ fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee" },
	],

	onload(report) {
		if (mc_hr()) report.page.add_inner_button(__("Punches"), () => mc_punches(report));
	},

	get_datatable_options(options) {
		return mc_hr() ? Object.assign(options, { checkboxColumn: true }) : options;
	},
};
