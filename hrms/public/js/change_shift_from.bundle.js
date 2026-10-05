// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

// HR: "Change shift from..." — move a person to another shift from a date, or
// give them different shifts on different weekdays (Mon-Thu 10-7, Fri 10-4).
//
// Owner, 5 Oct 2026: HR could not move someone from 9-6 to 10-7. Cancelling the
// old assignment is refused once punches exist ("linked to Employee Checkin")
// and a submitted assignment keeps no editable shift. The server endpoint
// hrms.api.roster.change_shift_from ENDS the old assignment the day before
// instead, so the past is never touched. This dialog only asks for the date and
// the shift(s) and says, before anything is written, what will change.
//
// A weekday nobody covers gets NO shift (owner: the choice that suits better).
// The preview names those days so HR cannot miss one.
//
// Loaded at boot (hooks.py app_include_js). Doors: the Shift Assignment form
// (Actions) and the Desk Roster row menu. Tests: change_shift_from.bundle.test.js

frappe.provide("hrms.change_shift");

const CS_API = "hrms.api.roster.change_shift_from";
const CS_HR_ROLES = ["HR User", "HR Manager"];
const CS_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

hrms.change_shift.enabled = function () {
	// the server decides (HR_SEE_ALL_ROLES); this only hides a button nobody else can use
	return CS_HR_ROLES.some((role) => frappe.user.has_role(role));
};

// the rows to send: [{shift_type, days}], days null = every day
hrms.change_shift.payload = function (rows, different) {
	return rows
		.filter((row) => row.shift)
		.map((row) => ({
			shift_type: row.shift,
			days: different ? row.days.map((index) => CS_WEEKDAYS[index]) : null,
		}));
};

// what is missing, in plain words ([] = ready to send)
hrms.change_shift.problems = function (date, rows, different) {
	const found = [];
	if (!date) found.push(__("Pick the date."));
	if (!rows.some((row) => row.shift)) found.push(__("Pick the new shift."));
	if (different) {
		const picked = rows.filter((row) => row.shift);
		if (picked.some((row) => !row.days.length)) found.push(__("Say which days each shift covers."));
		const seen = new Set();
		for (const row of picked) {
			for (const index of row.days) {
				if (seen.has(index)) {
					found.push(__("{0} is on two shifts. Give each day one shift.", [CS_WEEKDAYS[index]]));
					return found;
				}
				seen.add(index);
			}
		}
	}
	return found;
};

// weekdays no shift covers, when HR picked different shifts on different days
hrms.change_shift.days_without_shift = function (rows, different) {
	if (!different) return [];
	const covered = new Set(rows.filter((row) => row.shift).flatMap((row) => row.days));
	return CS_WEEKDAYS.filter((_, index) => !covered.has(index));
};

// "2026-10-12" → "2026-10-11", by the calendar, never by today's clock
hrms.change_shift.day_before = function (date) {
	const [year, month, day] = String(date).split("-").map(Number);
	const before = new Date(Date.UTC(year, month - 1, day - 1));
	return before.toISOString().slice(0, 10);
};

function cs_escape(value) {
	return frappe.utils.escape_html(value === null || value === undefined ? "" : String(value));
}

// the "What will change" box
function cs_preview(date, rows, different, shift_names) {
	if (!date) return `<p class="text-muted">${__("Pick a date to see what changes.")}</p>`;
	const lines = [
		`<div>${__("Until {0}", [cs_escape(hrms.change_shift.day_before(date))])}: <b>${__("no change")}</b></div>`,
		`<div>${__("From {0}", [cs_escape(date)])}: ${rows
			.filter((row) => row.shift)
			.map((row) => {
				const where = different ? row.days.map((index) => CS_WEEKDAYS[index].slice(0, 3)).join(", ") : __("every day");
				return `<b>${cs_escape(shift_names[row.shift] || row.shift)}</b> (${cs_escape(where)})`;
			})
			.join("; ")}</div>`,
		`<div class="text-muted">${__("Days before this stay as they are.")}</div>`,
	];
	const free = hrms.change_shift.days_without_shift(rows, different);
	if (free.length) {
		lines.push(`<div class="text-warning">${__("No shift on: {0}.", [cs_escape(free.join(", "))])}</div>`);
	}
	return lines.join("");
}

// Opens the dialog for one employee. `current` is a line about the shift now, if known.
hrms.change_shift.open = function (employee, employee_name, current) {
	const state = { rows: [{ shift: "", days: [] }], different: false, shifts: {} };
	const dialog = new frappe.ui.Dialog({
		title: __("Change shift from a date"),
		fields: [
			{ fieldtype: "Data", fieldname: "who", label: __("Employee"), read_only: 1, default: `${employee}: ${employee_name || ""}` },
			{ fieldtype: "Date", fieldname: "start", label: __("Change from"), reqd: 1, change: () => refresh() },
			{ fieldtype: "HTML", fieldname: "now", options: current ? `<p class="text-muted">${cs_escape(current)}</p>` : "" },
			{ fieldtype: "Check", fieldname: "different", label: __("Different shifts on different days"), change: () => {
				state.different = !!dialog.get_value("different");
				if (!state.different) state.rows = state.rows.slice(0, 1);
				render_rows();
				refresh();
			} },
			{ fieldtype: "HTML", fieldname: "rows" },
			{ fieldtype: "Section Break", label: __("What will change") },
			{ fieldtype: "HTML", fieldname: "preview" },
			{ fieldtype: "HTML", fieldname: "error" },
		],
		primary_action_label: __("Change shift"),
		primary_action: () => submit(),
	});

	function show_error(message) {
		dialog.get_field("error").$wrapper.html(message ? `<p class="text-danger">${cs_escape(message)}</p>` : "");
	}

	function refresh() {
		show_error("");
		dialog.get_field("preview").$wrapper.html(
			cs_preview(dialog.get_value("start"), state.rows, state.different, state.shifts)
		);
	}

	function render_rows() {
		const wrap = dialog.get_field("rows").$wrapper.empty();
		state.rows.forEach((row, at) => {
			const box = $(`<div class="cs-row" style="margin-bottom:12px"></div>`).appendTo(wrap);
			const select = $(`<select class="form-control" aria-label="${__("New shift")}"></select>`).appendTo(box);
			select.append(`<option value="">${__("Pick a shift")}</option>`);
			Object.entries(state.shifts).forEach(([name, label]) =>
				select.append(`<option value="${cs_escape(name)}" ${name === row.shift ? "selected" : ""}>${cs_escape(label)}</option>`)
			);
			select.on("change", () => {
				row.shift = select.val();
				refresh();
			});
			if (state.different) {
				const chips = $(`<div style="margin-top:6px" role="group"></div>`).appendTo(box);
				CS_WEEKDAYS.forEach((day, index) => {
					const used = state.rows.some((other, n) => n !== at && other.days.includes(index));
					const on = row.days.includes(index);
					$(`<button type="button" class="btn btn-xs ${on ? "btn-primary" : "btn-default"}" ${used ? "disabled" : ""} style="margin-right:4px">${day.slice(0, 3)}</button>`)
						.appendTo(chips)
						.on("click", () => {
							row.days = on ? row.days.filter((i) => i !== index) : [...row.days, index].sort();
							render_rows();
							refresh();
						});
				});
			}
		});
		if (state.different) {
			$(`<button type="button" class="btn btn-xs btn-default">${__("Add another shift")}</button>`)
				.appendTo(wrap)
				.on("click", () => {
					state.rows.push({ shift: "", days: [] });
					render_rows();
				});
		}
	}

	function submit() {
		const problems = hrms.change_shift.problems(dialog.get_value("start"), state.rows, state.different);
		if (problems.length) return show_error(problems[0]);
		if (state.busy) return; // a second press while saving does nothing
		state.busy = true;
		dialog.get_primary_btn().prop("disabled", true);
		frappe.call({
			method: CS_API,
			type: "POST",
			args: {
				employee,
				start_date: dialog.get_value("start"),
				shifts: JSON.stringify(hrms.change_shift.payload(state.rows, state.different)),
			},
			callback: () => {
				dialog.hide();
				frappe.show_alert({ message: __("Done. Shift changes from {0}.", [dialog.get_value("start")]), indicator: "green" });
				if (cur_frm) cur_frm.reload_doc();
				if (cur_list) cur_list.refresh();
			},
			error: () => {
				// the server's own words (a worked day names the day); nothing was changed
				const raw = (frappe.messages && frappe.messages.slice(-1)[0]) || "";
				show_error(String(raw).replace(/<[^>]+>/g, "") || __("Nothing was changed. Try again."));
			},
			always: () => {
				state.busy = false;
				dialog.get_primary_btn().prop("disabled", false);
			},
		});
	}

	frappe.db.get_list("Shift Type", { fields: ["name", "start_time", "end_time"], limit: 200 }).then((list) => {
		list.forEach((s) => (state.shifts[s.name] = `${s.name}`));
		render_rows();
		refresh();
	});
	dialog.show();
};

// the form door: Actions > Change shift from...
frappe.ui.form.on("Shift Assignment", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || !hrms.change_shift.enabled()) return;
		frm.add_custom_button(
			__("Change shift from..."),
			() => hrms.change_shift.open(frm.doc.employee, frm.doc.employee_name, `${frm.doc.shift_type}, from ${frm.doc.start_date}`),
			__("Actions")
		);
	},
});
