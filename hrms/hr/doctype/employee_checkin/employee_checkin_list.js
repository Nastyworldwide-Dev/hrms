frappe.listview_settings["Employee Checkin"] = {
	// HR reads this list to answer "did this punch count, and under which shift?".
	// The indicator answers it at a glance; the fields behind it are fetched
	// because the list only loads what it shows or is told to add.
	add_fields: [
		"offshift",
		"skip_auto_attendance",
		"attendance",
		"shift",
		"remote_approval_status",
	],
	get_indicator: function (doc) {
		if (doc.offshift) {
			return [__("Off-Shift"), "yellow", "offshift,=,1"];
		}
		if (doc.remote_approval_status === "Rejected") {
			return [__("Rejected"), "red", "remote_approval_status,=,Rejected"];
		}
		if (doc.skip_auto_attendance) {
			return [__("Skipped"), "orange", "skip_auto_attendance,=,1"];
		}
		if (doc.remote_approval_status === "Pending") {
			return [__("Awaiting approval"), "blue", "remote_approval_status,=,Pending"];
		}
		if (doc.attendance) {
			return [__("Counted"), "green", "attendance,is,set"];
		}
		return [__("Not counted yet"), "gray", "attendance,is,not set"];
	},
	onload: function (listview) {
		// The fix dialog. It lives in fix_day.bundle.js (loaded at boot by
		// hooks.app_include_js) and this list is its only door: ONE button
		// (owner, 21 Sep 2026: "Fix day" and "Fix days" folded into it). It is
		// registered HERE, in the list script Desk loads last, because a
		// doctype's listview_settings has exactly one owner: the bundle used to
		// assign this key itself and this file then overwrote it, so HR never
		// saw the button.
		if (typeof hrms !== "undefined" && hrms.fix_day && hrms.fix_day.enabled()) {
			listview.page.add_inner_button(__("Fix attendance"), () =>
				hrms.fix_day.from_taps(listview),
			);
		}
		listview.page.add_action_item(__("Fetch Shifts"), () => {
			const checkins = listview.get_checked_items().map((checkin) => checkin.name);
			frappe.call({
				method: "hrms.hr.doctype.employee_checkin.employee_checkin.bulk_fetch_shift",
				freeze: true,
				args: {
					checkins,
				},
			});
		});
	},
};
