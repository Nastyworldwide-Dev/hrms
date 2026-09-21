// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// HR edits the report like a master spreadsheet. Every write goes through
// hrms.api.attendance_master_edit, which carries a per-day revision so a day
// someone else changed is refused and reloaded, never overwritten.
// Grid tests: node --test hrms/hr/report/shift_attendance/shift_attendance.test.js

const SA_API = "hrms.api.attendance_master_edit.";
const SA_HR_ROLES = ["HR User", "HR Manager", "System Manager"];
const SA_MAX_ROWS = 200;
const SA_MAX_DAYS = 500; // attendance_master_edit.MAX_DAYS
const SA_GROUP = "Edit Attendance";
const SA_STATUSES = ["Present", "Absent", "Half Day", "Work From Home"];
const SA_TIME_FIELDS = ["in_time", "out_time"];
// Cells show "HH:MM:SS" for a same-day time and a formatted datetime otherwise.
const SA_TIME_RE = /(\d\d?):(\d\d)(?::(\d\d))?/;
const SA_EDITABLE = {
	attendance_date: { fieldtype: "Date", label: "Attendance Date" },
	shift: { fieldtype: "Link", options: "Shift Type", label: "Shift" },
	status: { fieldtype: "Select", options: SA_STATUSES.join("\n"), label: "Status" },
	in_time: { fieldtype: "Time", label: "In Time" },
	out_time: { fieldtype: "Time", label: "Out Time" },
};
const SA_BACKGROUND = { pending: "--bg-yellow", conflict: "--bg-orange", error: "--bg-red" };
const SA_CODE_TEXT = {
	conflict: "Changed by someone else — reloaded",
	fenced: "You are not allowed to edit this employee's attendance",
	not_found: "Employee or attendance not found",
	invalid: "A value is not valid",
	no_shift: "Choose a shift for this day first",
	draft: "A draft attendance is in the way; submit or delete it first",
	leave: "This day is a leave; change the leave application",
	mirrored: "Synced from another site; change it there",
	multiple_rows: "This day has more than one attendance row",
	financial_lock: "Payroll or a claim already uses this day; a System Manager must change it",
	shift_overlap: "Another shift assignment already covers this day",
	target_day_taken: "The chosen date already has attendance",
	nothing_to_remove: "There is no attendance on this day to remove",
	nothing_to_hand_back: "Nothing on this day was set by HR",
	not_hr_owned: "The system already manages this day",
	not_one_session: "A typed day longer than 20 hours is not one session; check the times",
	error: "Could not save this row; try again",
};

function sa_code_message(code) {
	return __(SA_CODE_TEXT[code] || "Could not save this row");
}

function sa_time_only(value) {
	const m = String(value || "").match(SA_TIME_RE);
	return m ? `${m[1].padStart(2, "0")}:${m[2]}:${m[3] || "00"}` : "";
}

function sa_clean(fieldname, value) {
	return SA_TIME_FIELDS.includes(fieldname) ? sa_time_only(value) : value || "";
}

function sa_key(employee, attendance_date) {
	return `${employee}|${attendance_date}`;
}

function sa_enabled() {
	return SA_HR_ROLES.some((role) => frappe.user.has_role(role));
}

class ShiftAttendanceGrid {
	constructor(report) {
		this.report = report;
		this.pending = new Map(); // day key -> {employee, attendance_date, changes}
		this.states = new Map(); // day key -> {kind: "conflict"|"error", message}
		// day key -> revision, read when the report data loaded (never at click or save:
		// a revision read at save always matches, so a stale screen would overwrite)
		this.revisions = new Map();
		this.loading = Promise.resolve();
		this.load_seq = 0;
		this.raw_refresh = null;
	}

	// Every refresh that is not the grid's own (a filter change, the Refresh
	// button) shows other rows, so edits staged for the old rows are dropped —
	// after a confirm — rather than saved for days no longer on screen.
	guard_refresh() {
		const report = this.report;
		if (this.raw_refresh || typeof report.refresh !== "function") return;
		this.raw_refresh = report.refresh.bind(report);
		report.refresh = (...args) => {
			if (!this.pending.size) {
				this.states.clear();
				return this.raw_refresh(...args);
			}
			return new Promise((resolve) => {
				frappe.confirm(
					__("Discard {0} unsaved change(s)? The report is reloading.", [this.pending.size]),
					() => {
						console.info("[ShiftAttendance] refresh discards", this.pending.size, "pending day(s)");
						this.pending.clear();
						this.states.clear();
						this.update_indicator();
						resolve(this.raw_refresh(...args));
					},
					() => {
						console.info("[ShiftAttendance] refresh declined; pending edits kept");
						resolve();
					}
				);
			});
		};
	}

	reload() {
		return this.raw_refresh ? this.raw_refresh() : this.report.refresh();
	}

	setup_toolbar() {
		const page = this.report.page;
		const group = __(SA_GROUP);
		page.add_inner_button(__("Edit selected"), () => this.edit_selected(), group);
		page.add_inner_button(__("Remove selected"), () => this.remove_selected(), group);
		page.add_inner_button(__("Add row"), () => this.add_row(), group);
		page.add_inner_button(__("Add / change shift"), () => this.change_shift(), group);
		page.add_inner_button(__("Hand back to system"), () => this.hand_back_selected(), group);
		page.add_inner_button(__("Punches"), () => this.punches(), group);
		console.info("[ShiftAttendance] edit tools shown");
		this.guard_refresh();
		this.update_indicator();
	}

	// A link, not an editor. The master edit above types a day's result; the
	// day's EVIDENCE — which taps count and which session they belong to — is
	// corrected on the Employee Checkin list, the only page that carries the
	// Fix Day tools (owner, 21 Sep 2026). This opens that list on the ticked day.
	punches() {
		const days = this.require_selection();
		if (!days.length) return;
		if (days.length !== 1) {
			frappe.msgprint(__("Tick exactly one day."));
			return;
		}
		const day = days[0];
		console.info("[ShiftAttendance] punches", day.employee, day.attendance_date);
		frappe.set_route("List", "Employee Checkin", {
			employee: day.employee,
			time: ["Between", [day.attendance_date, day.attendance_date]],
		});
	}

	// --- cell editing ---------------------------------------------------------

	make_editor(rowIndex, parent, column, data) {
		const fieldname = column && (column.fieldname || column.id);
		const spec = SA_EDITABLE[fieldname];
		if (!spec || !data || !data.employee || !data.attendance_date) return false;
		const control = frappe.ui.form.make_control({
			df: Object.assign({}, spec, { fieldname, label: __(spec.label) }),
			parent,
			render_input: true,
		});
		if (control.toggle_label) control.toggle_label(false);
		if (control.toggle_description) control.toggle_description(false);
		console.info("[ShiftAttendance] editing", fieldname, "row", rowIndex);
		return {
			initValue: (value) => control.set_value(spec.fieldtype === "Time" ? sa_time_only(value) : value),
			getValue: () => control.get_value(),
			setValue: (value) => this.stage(rowIndex, data, fieldname, value),
		};
	}

	stage(rowIndex, data, fieldname, value) {
		const key = sa_key(data.employee, data.attendance_date);
		const entry = this.pending.get(key) || {
			employee: data.employee,
			attendance_date: data.attendance_date,
			changes: {},
		};
		if (sa_clean(fieldname, value) === sa_clean(fieldname, data[fieldname])) {
			delete entry.changes[fieldname];
		} else {
			entry.changes[fieldname] = sa_clean(fieldname, value);
		}
		this.states.delete(key);
		if (Object.keys(entry.changes).length) {
			this.pending.set(key, entry);
		} else {
			this.pending.delete(key);
		}
		console.info("[ShiftAttendance] staged", key, fieldname, "pending days:", this.pending.size);
		this.update_indicator();
		this.repaint_row(rowIndex);
	}

	pending_value(data, fieldname) {
		if (!data) return undefined;
		const entry = this.pending.get(sa_key(data.employee, data.attendance_date));
		return entry && fieldname in entry.changes ? entry.changes[fieldname] : undefined;
	}

	row_state(data) {
		if (!data) return null;
		const key = sa_key(data.employee, data.attendance_date);
		if (this.states.has(key)) return this.states.get(key);
		return this.pending.has(key) ? { kind: "pending", message: __("Unsaved change") } : null;
	}

	repaint_row(rowIndex) {
		const datatable = this.report.datatable;
		if (!datatable || rowIndex === undefined) return;
		// The edited cell repaints itself; the rest of the row picks up the highlight
		// once DataTable has finished its own submit.
		setTimeout(() => {
			const cells = datatable.datamanager.getRow(rowIndex) || [];
			cells.forEach((cell) => datatable.cellmanager.refreshCell(cell, true));
		}, 0);
	}

	update_indicator() {
		const page = this.report.page;
		const count = this.pending.size;
		page.remove_inner_button(__("Save"));
		page.remove_inner_button(__("Discard"));
		if (!count) {
			page.clear_indicator();
			return;
		}
		page.set_indicator(__("{0} unsaved changes", [count]), "orange");
		page.add_inner_button(__("Discard"), () => this.discard());
		page.add_inner_button(__("Save"), () => this.save(), null, "primary");
	}

	discard() {
		console.info("[ShiftAttendance] discarded", this.pending.size, "pending day(s)");
		this.pending.clear();
		this.states.clear();
		this.update_indicator();
		this.reload();
	}

	// --- revisions ------------------------------------------------------------

	// One get_days call per SA_MAX_DAYS days, as the rows arrive. Only the latest
	// load writes, so a slow answer for old filters cannot land on new rows.
	load_revisions(rows) {
		const seq = ++this.load_seq;
		const days = new Map();
		(rows || []).forEach((row) => {
			if (!row || !row.employee || !row.attendance_date) return;
			const key = sa_key(row.employee, row.attendance_date);
			if (!days.has(key)) days.set(key, { employee: row.employee, attendance_date: row.attendance_date });
		});
		const items = Array.from(days.values());
		const chunks = [];
		for (let i = 0; i < items.length; i += SA_MAX_DAYS) chunks.push(items.slice(i, i + SA_MAX_DAYS));
		console.info("[ShiftAttendance] reading revisions for", items.length, "day(s) in", chunks.length, "call(s)");
		const reads = chunks.map((chunk) =>
			Promise.resolve(
				frappe.call({ method: SA_API + "get_days", args: { employee_dates: JSON.stringify(chunk) } })
			)
				.then((r) => (r && r.message && r.message.days) || {})
				.catch((error) => {
					console.warn("[ShiftAttendance] get_days failed for", chunk.length, "day(s)", error);
					return {};
				})
		);
		this.loading = Promise.all(reads).then((answers) => {
			if (seq !== this.load_seq) return;
			this.revisions.clear();
			answers.forEach((answer) =>
				Object.keys(answer).forEach((key) => {
					if (answer[key] && answer[key].revision) this.revisions.set(key, answer[key].revision);
				})
			);
		});
		return this.loading;
	}

	// A typed-in new day is not on screen, so its revision is read when it is added.
	read_day(employee, attendance_date) {
		return Promise.resolve(frappe.call({ method: SA_API + "get_day", args: { employee, attendance_date } }))
			.then((r) => (r && r.message && r.message.revision) || null)
			.catch((error) => {
				console.warn("[ShiftAttendance] get_day failed", sa_key(employee, attendance_date), error);
				return null;
			});
	}

	loaded_revision(employee, attendance_date) {
		return this.loading.then(() => this.revisions.get(sa_key(employee, attendance_date)) || null);
	}

	// --- save -----------------------------------------------------------------

	save() {
		const payload = [];
		this.pending.forEach((entry) => {
			payload.push({
				employee: entry.employee,
				attendance_date: entry.attendance_date,
				action: "edit",
				changes: Object.assign({}, entry.changes),
			});
		});
		console.info("[ShiftAttendance] save", payload.length, "day(s)");
		return payload.length ? this.submit(payload) : Promise.resolve();
	}

	selected_days() {
		const seen = new Map();
		(this.report.get_checked_items() || []).forEach((item) => {
			if (!item || !item.employee || !item.attendance_date) return;
			const key = sa_key(item.employee, item.attendance_date);
			if (!seen.has(key)) seen.set(key, item);
		});
		return Array.from(seen.values());
	}

	require_selection() {
		const days = this.selected_days();
		if (!days.length) frappe.msgprint(__("Tick one or more rows first."));
		return days;
	}

	// Rows for checked days with any unsaved cell edits folded in, so one day
	// never travels twice in the same save.
	rows_for(days, action, changes) {
		return days.map((day) => {
			const entry = this.pending.get(sa_key(day.employee, day.attendance_date));
			const merged = action === "remove" ? {} : Object.assign({}, entry && entry.changes, changes);
			return { employee: day.employee, attendance_date: day.attendance_date, action, changes: merged };
		});
	}

	submit(rows) {
		if (rows.length > SA_MAX_ROWS) {
			// ceiling: one save_rows call per save, upgrade: batch when HR routinely saves >200 days
			frappe.msgprint(__("Save at most {0} rows at a time; {1} are waiting.", [SA_MAX_ROWS, rows.length]));
			return Promise.resolve();
		}
		const reads = rows.map((row) =>
			row.action === "add"
				? this.read_day(row.employee, row.attendance_date)
				: this.loaded_revision(row.employee, row.attendance_date)
		);
		return Promise.all(reads).then((revisions) => this.send(rows, revisions));
	}

	send(rows, revisions) {
		const payload = [];
		const problems = [];
		rows.forEach((row, i) => {
			if (revisions[i]) {
				payload.push(Object.assign({}, row, { revision: revisions[i] }));
			} else {
				const text = __("Could not load this day; refresh the report and try again");
				this.mark(row, "error", text);
				problems.push({ row, text });
			}
		});
		console.info("[ShiftAttendance] save_rows", payload.length, "row(s),", problems.length, "unreadable");
		if (!payload.length) {
			this.finish(problems, 0);
			return Promise.resolve({ saved: 0, problems });
		}
		return Promise.resolve(
			frappe.call({
				method: SA_API + "save_rows",
				args: { rows: JSON.stringify(payload) },
				freeze: true,
				freeze_message: __("Saving attendance..."),
			})
		).then((r) => this.apply_results(payload, (r && r.message) || {}, problems));
	}

	apply_results(payload, message, problems) {
		const results = message.rows || [];
		let saved = 0;
		payload.forEach((row, index) => {
			const key = sa_key(row.employee, row.attendance_date);
			const result = results.find((r) => r.index === index);
			this.revisions.delete(key);
			if (result && result.ok) {
				saved += 1;
				this.pending.delete(key);
				this.states.delete(key);
			} else if (result && result.conflict) {
				// Reloaded, not rebased: the edit is dropped so a second click on Save
				// cannot overwrite what the other person wrote; HR re-enters it knowingly.
				const text = sa_code_message("conflict");
				this.pending.delete(key);
				this.mark(row, "conflict", text);
				problems.push({ row, text, current: result.current, tried: row.changes });
			} else {
				const text = result ? sa_code_message(result.code) : __("No answer from the server for this row");
				this.mark(row, "error", text);
				problems.push({ row, text, detail: result && result.error });
			}
		});
		console.info("[ShiftAttendance] saved", saved, "of", payload.length, "refused", problems.length);
		this.finish(problems, saved);
		return { saved, problems };
	}

	mark(row, kind, message) {
		this.states.set(sa_key(row.employee, row.attendance_date), { kind, message });
	}

	finish(problems, saved) {
		this.update_indicator();
		this.show_results(problems, saved);
		// the grid's own reload: refused rows are still on screen and stay pending
		this.reload();
	}

	show_results(problems, saved) {
		if (!problems.length) {
			frappe.show_alert({ message: __("{0} row(s) saved", [saved]), indicator: "green" });
			return;
		}
		console.info("[ShiftAttendance] showing", problems.length, "row problem(s)");
		frappe.msgprint({
			title: __("Saved {0}, {1} need attention", [saved, problems.length]),
			indicator: "orange",
			message: `<ul>${problems.map(sa_problem_line).join("")}</ul>`,
		});
	}

	// --- toolbar actions ------------------------------------------------------

	edit_selected() {
		const days = this.require_selection();
		if (!days.length) return;
		const dialog = new frappe.ui.Dialog({
			title: __("Edit {0} selected day(s)", [days.length]),
			fields: [
				{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\n" + SA_STATUSES.join("\n") },
				{ fieldname: "shift", label: __("Shift"), fieldtype: "Link", options: "Shift Type" },
				{ fieldname: "in_time", label: __("In Time"), fieldtype: "Time" },
				{ fieldname: "out_time", label: __("Out Time"), fieldtype: "Time" },
			],
			primary_action_label: __("Save"),
			primary_action: (values) => {
				const changes = sa_filled(values, ["status", "shift", "in_time", "out_time"]);
				if (!Object.keys(changes).length) return frappe.msgprint(__("Set at least one value."));
				dialog.hide();
				return this.submit(this.rows_for(days, "edit", changes));
			},
		});
		console.info("[ShiftAttendance] bulk edit for", days.length, "day(s)");
		dialog.show();
		return dialog;
	}

	change_shift() {
		const days = this.require_selection();
		if (!days.length) return;
		const dialog = new frappe.ui.Dialog({
			title: __("Add or change shift for {0} day(s)", [days.length]),
			fields: [{ fieldname: "shift", label: __("Shift"), fieldtype: "Link", options: "Shift Type", reqd: 1 }],
			primary_action_label: __("Save"),
			primary_action: (values) => {
				dialog.hide();
				return this.submit(this.rows_for(days, "edit", { shift: values.shift }));
			},
		});
		console.info("[ShiftAttendance] shift change for", days.length, "day(s)");
		dialog.show();
		return dialog;
	}

	remove_selected() {
		const days = this.require_selection();
		if (!days.length) return;
		console.info("[ShiftAttendance] remove asked for", days.length, "day(s)");
		return new Promise((resolve) => {
			frappe.confirm(
				__("Remove attendance for {0} day(s)? The punches are kept.", [days.length]),
				() => resolve(this.submit(this.rows_for(days, "remove", {}))),
				() => resolve()
			);
		});
	}

	add_row() {
		const current = (this.report.get_filter_values && this.report.get_filter_values()) || {};
		const dialog = new frappe.ui.Dialog({
			title: __("Add attendance row"),
			fields: [
				{ fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee", reqd: 1, default: current.employee },
				{ fieldname: "attendance_date", label: __("Attendance Date"), fieldtype: "Date", reqd: 1 },
				{ fieldname: "shift", label: __("Shift"), fieldtype: "Link", options: "Shift Type", default: current.shift },
				{ fieldname: "in_time", label: __("In Time"), fieldtype: "Time" },
				{ fieldname: "out_time", label: __("Out Time"), fieldtype: "Time" },
				{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: SA_STATUSES.join("\n"), default: "Present", reqd: 1 },
			],
			primary_action_label: __("Add"),
			primary_action: (values) => {
				dialog.hide();
				const changes = sa_filled(values, ["status", "shift", "in_time", "out_time"]);
				const day = { employee: values.employee, attendance_date: values.attendance_date };
				return this.submit([Object.assign(day, { action: "add", changes })]);
			},
		});
		console.info("[ShiftAttendance] add row dialog");
		dialog.show();
		return dialog;
	}

	hand_back_selected() {
		const days = this.require_selection();
		if (!days.length) return;
		const owned = days.filter((d) => d.hr_owned);
		const skipped = days.filter((d) => !d.hr_owned);
		console.info("[ShiftAttendance] hand back asked:", owned.length, "HR-edited,", skipped.length, "skipped");
		if (!owned.length) return frappe.msgprint(__("None of the selected rows were edited by HR."));
		return new Promise((resolve) => {
			frappe.confirm(
				__("Hand {0} day(s) back to the system? HR's row is cancelled and the punches are processed again.", [
					owned.length,
				]),
				() => resolve(this.run_hand_back(owned, skipped)),
				() => resolve()
			);
		});
	}

	run_hand_back(owned, skipped) {
		const problems = skipped.map((row) => ({ row, text: __("Not edited by HR; left as is") }));
		const tally = { saved: 0 };
		// hand_back takes one day per call; run them one after another
		let chain = Promise.resolve();
		owned.forEach((day) => {
			chain = chain.then(() => this.hand_back_day(day, problems, tally));
		});
		return chain.then(() => {
			console.info("[ShiftAttendance] handed back", tally.saved, "of", owned.length);
			this.finish(problems, tally.saved);
			return { saved: tally.saved, problems };
		});
	}

	hand_back_day(day, problems, tally) {
		const key = sa_key(day.employee, day.attendance_date);
		return this.loaded_revision(day.employee, day.attendance_date).then((revision) => {
			if (!revision) {
				return problems.push({ row: day, text: __("Could not load this day; refresh the report and try again") });
			}
			const args = { employee: day.employee, attendance_date: day.attendance_date, revision };
			return Promise.resolve(frappe.call({ method: SA_API + "hand_back", args, freeze: true })).then((r) => {
				const answer = (r && r.message) || {};
				this.revisions.delete(key);
				if (answer.ok) {
					tally.saved += 1;
					this.pending.delete(key);
					this.states.delete(key);
					return;
				}
				const text = sa_code_message(answer.code);
				console.info("[ShiftAttendance] hand back refused", key, answer.code);
				this.mark(day, answer.conflict ? "conflict" : "error", text);
				problems.push({ row: day, text, current: answer.current, detail: answer.conflict ? null : answer.error });
			});
		});
	}
}

function sa_filled(values, fieldnames) {
	const out = {};
	fieldnames.filter((f) => values && values[f]).forEach((f) => (out[f] = values[f]));
	return out;
}

function sa_describe(changes) {
	const esc = frappe.utils.escape_html;
	const label = (field) => __((SA_EDITABLE[field] || {}).label || field);
	return Object.keys(changes).map((f) => `${esc(label(f))} ${esc(changes[f] || "-")}`).join(", ");
}

function sa_current_row(current) {
	const rows = (current && current.attendance) || [];
	return rows.find((r) => Number(r.docstatus) === 1) || rows[0];
}

function sa_problem_line(p) {
	const esc = frappe.utils.escape_html;
	const now = p.current ? sa_current_row(p.current) : null;
	console.info("[ShiftAttendance] row problem", p.row.employee, p.row.attendance_date, p.text);
	let line = `<b>${esc(p.row.employee)}</b> ${esc(p.row.attendance_date)}: ${esc(p.text)}`;
	if (p.detail) line += `<br><span class="text-muted">${esc(p.detail)}</span>`;
	if (p.current && now) line += `<br><span class="text-muted">${__("Now")}: ${sa_describe(sa_pick(now))}</span>`;
	if (p.current && !now) line += `<br><span class="text-muted">${__("Now: no attendance on this day")}</span>`;
	if (p.tried && Object.keys(p.tried).length) {
		line += `<br><span class="text-muted">${__("Your change")}: ${sa_describe(p.tried)}</span>`;
	}
	return `<li>${line}</li>`;
}

function sa_pick(row) {
	return { status: row.status, shift: row.shift, in_time: row.in_time, out_time: row.out_time };
}

function sa_grid(report) {
	if (report && !report.__shift_attendance_grid) report.__shift_attendance_grid = new ShiftAttendanceGrid(report);
	return report ? report.__shift_attendance_grid : null;
}

function sa_highlight(value, state, staged) {
	const style = `display:block;${staged ? "font-weight:600;" : ""}background-color:var(${SA_BACKGROUND[state.kind]})`;
	return `<span title="${frappe.utils.escape_html(state.message)}" style="${style}">${value}</span>`;
}

function sa_bind_single_click(datatable) {
	const body = datatable.bodyScrollable;
	if (!body || body.__sa_click_bound) return;
	body.__sa_click_bound = true;
	// one click edits, like a spreadsheet; DataTable on its own waits for a double click
	body.addEventListener("click", (event) => {
		const cell = event.target.closest && event.target.closest(".dt-cell");
		if (!cell || cell.classList.contains("dt-cell--editing")) return;
		const column = datatable.getColumn(Number(cell.dataset.colIndex));
		if (column && SA_EDITABLE[column.fieldname || column.id]) datatable.cellmanager.activateEditing(cell);
	});
	console.info("[ShiftAttendance] single-click editing bound");
}

frappe.query_reports["Shift Attendance"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_end(),
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "shift",
			label: __("Shift Type"),
			fieldtype: "Link",
			options: "Shift Type",
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "late_entry",
			label: __("Late Entry"),
			fieldtype: "Check",
		},
		{
			fieldname: "early_exit",
			label: __("Early Exit"),
			fieldtype: "Check",
		},
		{
			fieldname: "consider_grace_period",
			label: __("Consider Grace Period"),
			fieldtype: "Check",
			default: 1,
		},
		{
			fieldname: "include_attendance_without_checkins",
			label: __("Include Shift Attendance Without Checkins"),
			fieldtype: "Check",
			default: 0,
		},
	],
	onload(report) {
		if (sa_enabled()) sa_grid(report).setup_toolbar();
	},
	after_refresh(report) {
		// every load, filters changed or not: the revisions belong to these rows
		if (!sa_enabled()) return;
		return sa_grid(report).load_revisions(report.data);
	},
	get_datatable_options(options) {
		if (!sa_enabled()) return options;
		return Object.assign(options, {
			checkboxColumn: true,
			getEditor(colIndex, rowIndex, value, parent, column, row, data) {
				const grid = sa_grid(frappe.query_report);
				return grid ? grid.make_editor(rowIndex, parent, column, data) : false;
			},
		});
	},
	after_datatable_render(datatable) {
		if (!sa_enabled() || !datatable) return;
		// query_report builds every column with editable: false on each render
		(datatable.getColumns() || []).forEach((column) => {
			if (SA_EDITABLE[column.fieldname || column.id]) column.editable = true;
		});
		sa_bind_single_click(datatable);
	},
	formatter(value, row, column, data, default_formatter) {
		const grid = sa_enabled() ? sa_grid(frappe.query_report) : null;
		const staged = grid ? grid.pending_value(data, column.fieldname) : undefined;
		value = default_formatter(staged === undefined ? value : staged, row, column, data);
		if (
			(column.fieldname === "in_time" && data && data.late_entry) ||
			(column.fieldname === "out_time" && data && data.early_exit)
		) {
			value = `<span style='color:red!important'>${value}</span>`;
		}
		if (!grid || !data) return value;
		if (column.fieldname === "status" && data.hr_owned) {
			value += ` <span class="indicator-pill blue" title="${__("Edited by HR")}">${__("HR")}</span>`;
		}
		const state = grid.row_state(data);
		return state ? sa_highlight(value, state, staged !== undefined) : value;
	},
	__grid: { ShiftAttendanceGrid, sa_code_message, sa_time_only, SA_CODE_TEXT },
};
