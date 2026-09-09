// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

frappe.query_reports["Checkin Provenance Audit"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.month_start(), -1),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "kind",
			label: __("Kind"),
			fieldtype: "Select",
			options: ["Overwritten", "Mirrored", "Local", "All"],
			default: "Overwritten",
		},
	],

	onload(report) {
		// The server side is System Manager only; the button is a dry run first
		// and never writes without the confirm below.
		report.page.add_inner_button(__("Recover Overwritten Check-ins"), () => recover(report));
	},
};

function recover(report) {
	const args = {
		from_date: report.get_filter_value("from_date"),
		to_date: report.get_filter_value("to_date"),
	};
	frappe.call({
		method: "hrms.sync.checkin_recovery.recover_overwritten_checkins",
		args: { ...args, dry_run: 1 },
		freeze: true,
		callback: ({ message }) => {
			const inserts = (message.plan || []).filter((e) => e.action === "insert");
			if (!inserts.length) {
				frappe.msgprint(__("Nothing to recover in this window."));
				return;
			}
			frappe.msgprint({
				title: __("Dry run: {0} check-ins would be inserted", [inserts.length]),
				message: planTable(inserts),
				wide: true,
			});
			frappe.confirm(
				__("Insert {0} recovered check-ins now? Existing rows are never changed.", [
					inserts.length,
				]),
				() =>
					frappe.call({
						method: "hrms.sync.checkin_recovery.recover_overwritten_checkins",
						args: { ...args, dry_run: 0 },
						freeze: true,
						callback: ({ message: done }) => {
							frappe.show_alert({
								message: __("Inserted {0}, failed {1}", [
									done.inserted,
									done.failed,
								]),
								indicator: done.failed ? "orange" : "green",
							});
							report.refresh();
						},
					})
			);
		},
	});
}

function planTable(entries) {
	const rows = entries
		.map(
			(e) =>
				`<tr><td>${frappe.utils.escape_html(
					e.employee
				)}</td><td>${frappe.utils.escape_html(String(e.time))}</td>` +
				`<td>${frappe.utils.escape_html(e.log_type)}</td><td>${frappe.utils.escape_html(
					e.confidence
				)}</td><td>${frappe.utils.escape_html(e.source_name)}</td></tr>`
		)
		.join("");
	return (
		`<table class="table table-bordered table-sm"><thead><tr><th>${__(
			"Employee"
		)}</th><th>${__("Time")}</th>` +
		`<th>${__("Type")}</th><th>${__("Type source")}</th><th>${__(
			"Overwritten row"
		)}</th></tr></thead><tbody>${rows}</tbody></table>`
	);
}
