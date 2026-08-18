// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Shift Type", {
	refresh: function (frm) {
		if (frm.doc.__islocal) return;

		hrms.add_shift_tools_button_to_form(frm, {
			action: "Assign Shift",
			shift_type: frm.doc.name,
		});

		frm.add_custom_button(__("Mark Attendance"), () => {
			if (!frm.doc.enable_auto_attendance) {
				frm.scroll_to_field("enable_auto_attendance");
				frappe.throw(__("Please Enable Auto Attendance and complete the setup first."));
			}

			if (!frm.doc.process_attendance_after) {
				frm.scroll_to_field("process_attendance_after");
				frappe.throw(__("Please set {0}.", [__("Process Attendance After").bold()]));
			}

			if (!frm.doc.last_sync_of_checkin) {
				frm.scroll_to_field("last_sync_of_checkin");
				frappe.throw(__("Please set {0}.", [__("Last Sync of Checkin").bold()]));
			}

			frm.call({
				doc: frm.doc,
				method: "process_auto_attendance",
				freeze: true,
				args: {
					is_manually_triggered: true,
				},
				callback: (r) => {
					frappe.msgprint(__(r.message));
				},
			});
		});
	},
});

// Mirror a Fixed break's window length into Break Duration (Hours) as the
// row is edited, so the grid shows the configured window before save. The
// server recomputes on validate — this is display-only convenience.
function sync_break_duration(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if ((row.break_type || "Fixed") === "Flexible") return;

	const to_seconds = (t) => {
		if (!t) return null;
		const parts = String(t).split(":").map(Number);
		return parts[0] * 3600 + (parts[1] || 0) * 60 + (parts[2] || 0);
	};

	const start = to_seconds(row.start_time);
	const end = to_seconds(row.end_time);
	const hours = start !== null && end !== null && end > start ? Math.round(((end - start) / 3600) * 100) / 100 : 0;
	if (row.break_hours !== hours) {
		console.info("[ShiftType] Break row duration synced:", { start: row.start_time, end: row.end_time, hours });
		frappe.model.set_value(cdt, cdn, "break_hours", hours);
	}
}

frappe.ui.form.on("Shift Break", {
	break_type(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.break_type === "Flexible") {
			// A window-derived value must not silently become the Flexible
			// deduction — clear it so the user enters the duration explicitly.
			if (row.break_hours) {
				console.info("[ShiftType] Break row flipped to Flexible, clearing derived duration:", row.break_hours);
				frappe.model.set_value(cdt, cdn, "break_hours", 0);
			}
			return;
		}
		sync_break_duration(frm, cdt, cdn);
	},
	start_time: sync_break_duration,
	end_time: sync_break_duration,
});
