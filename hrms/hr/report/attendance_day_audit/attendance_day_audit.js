// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Attendance Day Audit"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -14),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{ fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee" },
		{
			fieldname: "verdict",
			label: __("Verdict"),
			fieldtype: "Select",
			options: [
				"All",
				"punches-skip-stamped",
				"punches-linked-to-cancelled-row",
				"unread-punches",
				"half-day-one-punch",
				"shift-mismatch",
				"before-process-attendance-after",
				"after-last-sync",
				"row-manual",
				"row-mirrored",
				"row-leave",
				"punches-rejected",
				"punches-mirrored",
				"marked",
				"no-punches",
			],
			default: "All",
		},
	],

	onload(report) {
		// Server side is System Manager only; dry run first, then an explicit confirm.
		report.page.add_inner_button(__("Repair Skip Stamps and Dead Links"), () =>
			repair(report)
		);
	},
};

function repair(report) {
	const args = {
		from_date: report.get_filter_value("from_date"),
		to_date: report.get_filter_value("to_date"),
	};
	frappe.call({
		method: "hrms.utils.attendance_day_audit.repair_attendance_days",
		args: { ...args, dry_run: 1 },
		freeze: true,
		callback: ({ message }) => {
			const plan = message.plan || [];
			if (!plan.length) {
				frappe.msgprint(__("Nothing to repair in this window."));
				return;
			}
			const esc = frappe.utils.escape_html;
			const rows = plan
				.map(
					(p) =>
						`<tr><td>${esc(p.employee)}</td><td>${esc(p.date)}</td><td>${esc(
							p.action
						)}</td><td>${p.punches.length}</td></tr>`
				)
				.join("");
			frappe.msgprint({
				title: __("Dry run: {0} employee-day(s)", [plan.length]),
				message: `<table class="table table-bordered table-sm"><thead><tr><th>${__(
					"Employee"
				)}</th><th>${__("Date")}</th><th>${__("Action")}</th><th>${__(
					"Punches"
				)}</th></tr></thead><tbody>${rows}</tbody></table>`,
				wide: true,
			});
			frappe.confirm(
				__(
					"Clear the old skip stamps / dead links on {0} day(s) and queue the hourly job now? Attendance rows themselves are not changed.",
					[plan.length]
				),
				() =>
					frappe.call({
						method: "hrms.utils.attendance_day_audit.repair_attendance_days",
						args: { ...args, dry_run: 0, remark_now: 1 },
						freeze: true,
						callback: ({ message: done }) => {
							frappe.show_alert({
								message: __("Cleared {0} punch(es); hourly job queued: {1}", [
									done.touched,
									done.remark_queued ? __("yes") : __("no"),
								]),
								indicator: "green",
							});
							report.refresh();
						},
					})
			);
		},
	});
}
