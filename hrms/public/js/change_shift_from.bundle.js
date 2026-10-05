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

// The server's own words from a Frappe error response (_server_messages is a JSON list of
// JSON strings). "" when there is nothing readable: the caller falls back to plain words.
hrms.change_shift.server_message = function (reply) {
	try {
		const list = JSON.parse((reply && reply._server_messages) || "[]");
		if (!list.length) return "";
		const message = JSON.parse(list[list.length - 1]).message || "";
		return String(message).replace(/<[^>]+>/g, "").trim();
	} catch (error) {
		return "";
	}
};

// What a weekday chip says to a screen reader: the full day, whether it is on, and why not.
hrms.change_shift.chip_state = function (day, on, used) {
	return {
		label: used ? __("{0} (on another shift)", [day]) : day,
		pressed: on ? "true" : "false",
		title: used ? __("{0} is on another shift", [day]) : "",
	};
};

// "2 changes after this date will be removed: 17 Oct (Off Day), ..." ("" when none).
hrms.change_shift.removed_notice = function (removed) {
	if (!removed || !removed.length) return "";
	const list = removed
		.map((row) => `${cs_escape(row.start_date)}${row.day_type && row.day_type !== "None" ? ` (${cs_escape(row.day_type)})` : ""}`)
		.join(", ");
	const head =
		removed.length === 1
			? __("1 change after this date will be removed")
			: __("{0} changes after this date will be removed", [removed.length]);
	return `<div class="text-warning" role="status"><b>${__("Warning:")}</b> ${head}: ${list}.</div>`;
};

// The server refused this date (a worked day, a mirrored assignment): said where HR looks.
hrms.change_shift.refusal_notice = function (refused) {
	return refused ? `<div class="text-danger" role="alert">${cs_escape(refused)}</div>` : "";
};

function cs_escape(value) {
	return frappe.utils.escape_html(value === null || value === undefined ? "" : String(value));
}

// the "What will change" box
function cs_preview(date, rows, different, shift_names, server) {
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
		lines.push(`<div class="text-warning"><b>${__("Warning:")}</b> ${__("No shift on: {0}.", [cs_escape(free.join(", "))])}</div>`);
	}
	if (server) {
		lines.push(hrms.change_shift.removed_notice(server.removed));
		lines.push(hrms.change_shift.refusal_notice(server.refused));
	}
	return lines.join("");
}

// Opens the dialog for one employee. `current` is a line about the shift now, if known.
hrms.change_shift.open = function (employee, employee_name, current) {
	const state = { rows: [{ shift: "", days: [] }], different: false, shifts: {}, server: null, ask: 0 };
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
		// the container already exists with role=alert, so the text is announced when it arrives
		dialog.get_field("error").$wrapper.html(`<div role="alert" class="text-danger">${message ? cs_escape(message) : ""}</div>`);
	}

	function draw() {
		dialog.get_field("preview").$wrapper.html(
			`<div aria-live="polite">${cs_preview(dialog.get_value("start"), state.rows, state.different, state.shifts, state.server)}</div>`
		);
	}

	// Asks the server what this would do (what it drops, whether the date is refused). The
	// newest answer wins; a slow older one is ignored.
	function ask_server() {
		const date = dialog.get_value("start");
		const shifts = hrms.change_shift.payload(state.rows, state.different);
		if (!date || !shifts.length) {
			state.server = null;
			return draw();
		}
		const mine = ++state.ask;
		frappe.call({
			method: "hrms.api.roster.preview_shift_change",
			type: "POST",
			args: { employee, start_date: date, shifts: JSON.stringify(shifts) },
			callback: (r) => {
				if (mine !== state.ask) return;
				state.server = r && r.message ? r.message : null;
				draw();
			},
			error: () => {
				if (mine === state.ask) state.server = null;
			},
		});
	}

	function refresh() {
		show_error("");
		draw();
		ask_server();
	}

	function render_rows() {
		const wrap = dialog.get_field("rows").$wrapper.empty();
		state.rows.forEach((row, at) => {
			const box = $(`<div class="cs-row mb-3"></div>`).appendTo(wrap);
			const id = `cs-shift-${at}`;
			const heading = state.different ? __("Shift {0}", [at + 1]) : __("New shift");
			$(`<label class="control-label" for="${id}">${cs_escape(heading)}</label>`).appendTo(box);
			const select = $(`<select class="form-control" id="${id}"></select>`).appendTo(box);
			select.append(`<option value="">${__("Pick a shift")}</option>`);
			Object.entries(state.shifts).forEach(([name, label]) =>
				select.append(`<option value="${cs_escape(name)}" ${name === row.shift ? "selected" : ""}>${cs_escape(label)}</option>`)
			);
			select.on("change", () => {
				row.shift = select.val();
				refresh();
			});
			if (state.different) {
				const chips = $(`<div class="mt-2" role="group" aria-label="${cs_escape(__("Days for shift {0}", [at + 1]))}"></div>`).appendTo(box);
				CS_WEEKDAYS.forEach((day, index) => {
					const used = state.rows.some((other, n) => n !== at && other.days.includes(index));
					const on = row.days.includes(index);
					const chip = hrms.change_shift.chip_state(day, on, used);
					$(`<button type="button" class="btn btn-sm ${on ? "btn-primary" : "btn-default"} mr-1 mb-1" aria-pressed="${chip.pressed}" aria-label="${cs_escape(chip.label)}" title="${cs_escape(chip.title)}" data-cs-row="${at}" data-cs-day="${index}" ${used ? "disabled" : ""}>${day.slice(0, 3)}</button>`)
						.appendTo(chips)
						.on("click", () => {
							row.days = (on ? row.days.filter((i) => i !== index) : [...row.days, index]).sort((a, b) => a - b);
							render_rows();
							refresh();
							// the chip was rebuilt: put the keyboard back on it
							wrap.find(`[data-cs-row="${at}"][data-cs-day="${index}"]`).trigger("focus");
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
		dialog.get_primary_btn().prop("disabled", true).text(__("Changing..."));
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
			error: (reply) => {
				// the server's own words (a worked day names the day); nothing was changed
				show_error(hrms.change_shift.server_message(reply) || __("Nothing was changed. Try again."));
			},
			always: () => {
				state.busy = false;
				dialog.get_primary_btn().prop("disabled", false).text(__("Change shift"));
			},
		});
	}

	frappe.db.get_list("Shift Type", { fields: ["name", "start_time", "end_time"], limit: 500 }).then((list) => {
		list.forEach((s) => (state.shifts[s.name] = `${s.name} (${String(s.start_time).slice(0, 5)}-${String(s.end_time).slice(0, 5)})`));
		render_rows();
		refresh();
	});
	dialog.show();
	dialog.get_field("start").$input && dialog.get_field("start").$input.trigger("focus");
};

// the form door: Actions > Change shift from...
frappe.ui.form.on("Shift Assignment", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || !hrms.change_shift.enabled()) return;
		frm.add_custom_button(
			__("Change shift from..."),
			() => hrms.change_shift.open(frm.doc.employee, frm.doc.employee_name, __("{0}, from {1}", [frm.doc.shift_type, frm.doc.start_date])),
			__("Actions")
		);
	},
});
