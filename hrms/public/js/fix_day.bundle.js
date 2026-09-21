// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

// HR Fix Day — one employee, one day.
//
// Owner rule (16 Sep 2026): HR corrects the EVIDENCE, never the result. This
// screen shows every tap of the day and lets HR say which taps are one session,
// which shift a tap belongs to, which taps count, and which tap is missing. It
// has NO hours field and NO overtime field on purpose: the engine recomputes
// hours, break, the OT ladder and claimability through
// hrms.api.attendance_fix_day -> hrms.utils.day_remark, and answers with the
// day before and after, which is what the screen shows.
//
// Loaded at boot (hooks.py app_include_js). Its only doors are the "Fix day"
// and "Fix days" buttons on the Employee Checkin list (owner, 21 Sep 2026: the
// tool lives on the punches page only; the Attendance list and the two reports
// link there with "Punches"). "Fix days" is the range form: tick, choose a
// shift, preview, apply — every punch in the range is restamped to that shift,
// IN and OUT alike, and each day is rebuilt by the same engine.
//
// Tests: hrms/tests/test_fix_day_screen.py

frappe.provide("hrms.fix_day");

const FD_API = "hrms.api.attendance_fix_day.";
const FD_HR_ROLES = ["HR User", "HR Manager", "System Manager"];
const FD_STATE_COLOUR = {
	counted: "green",
	"HR-entered": "blue",
	skipped: "grey",
	"off-shift": "grey",
	"awaiting approval": "orange",
	rejected: "red",
};

function fd_enabled() {
	return FD_HR_ROLES.some((role) => frappe.user.has_role(role));
}

function fd_escape(value) {
	return frappe.utils.escape_html(value === null || value === undefined ? "" : String(value));
}

function fd_clock(value) {
	const match = String(value || "").match(/(\d\d?):(\d\d)/);
	return match ? `${match[1].padStart(2, "0")}:${match[2]}` : "—";
}

// One Attendance row in words. Hours and overtime are SHOWN here and never
// sent back: this screen has no control that could edit them.
//
// It leads with the row's NAME and SHIFT because that is how HR matches this
// line to the Attendance list, and on a two-row day it is the only way to tell
// the rows apart. Owner, 17 Sep 2026, on Norazlin's 4 September: "no such 7pm
// stuff, the number att is different?" — the 7PM row was on the screen the
// whole time, printed as a bare status and two zeroes.
function fd_row_line(row) {
	return __("{0} · {1} · {2} · in {3} · out {4} · {5} h worked · {6} h OT", [
		fd_escape(row.name || "—"),
		fd_escape(row.shift || __("no shift")),
		fd_escape(row.status || "—"),
		fd_clock(row.in_time),
		fd_clock(row.out_time),
		fd_escape(row.hours),
		fd_escape(row.overtime),
	]);
}

function fd_day_lines(rows) {
	if (!rows || !rows.length) return __("no attendance row");
	return rows.map(fd_row_line).join("<br>");
}

function fd_call(method, args) {
	return Promise.resolve(
		frappe.call({ method, args, freeze: true, freeze_message: __("Fixing the day...") })
	).then((answer) => (answer && answer.message) || null);
}

class FixDayScreen {
	constructor({ employee, date, on_close }) {
		this.employee = employee;
		this.date = date;
		this.on_close = on_close;
		this.selection = new Set();
		this.last_fix = null;
	}

	show() {
		this.dialog = new frappe.ui.Dialog({
			title: __("Fix day"),
			size: "large",
			fields: [{ fieldname: "screen", fieldtype: "HTML" }],
			primary_action_label: __("Close"),
			primary_action: () => this.close(),
		});
		this.dialog.show();
		console.info("[FixDay] opened", this.employee, this.date);
		return this.reload();
	}

	close() {
		this.dialog.hide();
		if (this.on_close) this.on_close();
	}

	reload() {
		return fd_call(FD_API + "get_day", { employee: this.employee, date: this.date }).then((day) => {
			this.day = day || {};
			this.selection.clear();
			this.render();
			return this.day;
		});
	}

	// --- painting -------------------------------------------------------------

	render() {
		const day = this.day || {};
		const wrapper = this.dialog.fields_dict.screen.$wrapper;
		wrapper.html(
			[
				this.header(day),
				this.taps_html(day),
				this.attendance_html(day),
				day.blocked ? this.blocked_html(day) : this.notice_html(day) + this.actions_html(),
			].join("")
		);
		wrapper.off("click.fixday").on("click.fixday", "[data-fd-action]", (event) => {
			this.act(event.currentTarget.getAttribute("data-fd-action"));
		});
		wrapper.off("change.fixday").on("change.fixday", "[data-fd-tap]", (event) => {
			const name = event.currentTarget.getAttribute("data-fd-tap");
			if (event.currentTarget.checked) this.selection.add(name);
			else this.selection.delete(name);
			console.info("[FixDay] selected", this.selection.size, "tap(s)");
		});
	}

	header(day) {
		const owner = day.owner
			? `<span class="indicator-pill blue">${fd_escape(day.owner)}</span>`
			: `<span class="text-muted">${__("owner not classified yet")}</span>`;
		return `<div class="mb-3"><b>${fd_escape(day.employee_name || day.employee)}</b> —
			${fd_escape(day.date)} ${owner}</div>`;
	}

	// A day that is usable but not yet rebuildable — two attendance rows — says
	// so here. It is not `blocked`: the button that ends a two-row day is one of
	// the ones below, so hiding them would be the dead end it is warning about.
	notice_html(day) {
		if (!day.notice || day.notice === day.blocked) return "";
		return `<div class="alert alert-warning mb-3">${fd_escape(day.notice)}</div>`;
	}

	taps_html(day) {
		const rows = (day.taps || [])
			.map((tap) => {
				const colour = FD_STATE_COLOUR[tap.state] || "grey";
				// A mirrored tap IS selectable: taking it over is the only way to
				// fix its day, and it was the one punch HR could not tick (owner,
				// 18 Sep 2026). Every other action still refuses it server-side.
				const box = `<input type="checkbox" data-fd-tap="${fd_escape(tap.name)}">`;
				return `<tr>
					<td>${box}</td>
					<td>${fd_clock(tap.time)}</td>
					<td>${fd_escape(tap.log_type || "—")}</td>
					<td>${fd_escape(tap.shift || "—")}</td>
					<td><span class="indicator-pill ${colour}">${fd_escape(tap.state)}</span></td>
					<td class="text-muted small">${fd_escape(tap.device_id || "")}</td>
				</tr>`;
			})
			.join("");
		return `<h6>${__("Taps")}</h6>
			<table class="table table-bordered table-sm">
				<thead><tr>
					<th></th><th>${__("Time")}</th><th>${__("Type")}</th>
					<th>${__("Shift")}</th><th>${__("State")}</th><th>${__("Device")}</th>
				</tr></thead>
				<tbody>${rows || `<tr><td colspan="6">${__("No taps on this day.")}</td></tr>`}</tbody>
			</table>`;
	}

	attendance_html(day) {
		return `<h6>${__("Attendance")}</h6><div class="mb-3">${fd_day_lines(day.attendance)}</div>`;
	}

	blocked_html(day) {
		return `<div class="alert alert-warning">${fd_escape(day.blocked)}</div>`;
	}

	// No hours and no overtime input: five actions on the evidence, and the undo.
	actions_html() {
		const button = (action, label) =>
			`<button class="btn btn-default btn-sm mr-2" data-fd-action="${action}">${label}</button>`;
		const primary = (action, label) =>
			`<button class="btn btn-primary btn-sm mr-2" data-fd-action="${action}">${label}</button>`;
		return `<div class="mt-3">
			${primary("rebuild", __("Rebuild this day"))}
		</div>
		<div class="text-muted small mt-2 mb-2">
			${__("One press: it shows what it will do, you say why, and the day is rebuilt. The buttons below are for the days it cannot read.")}
		</div>
		<div class="mt-3">
			${button("pair", __("Pair as one session"))}
			${button("move", __("Move to shift / day"))}
			${button("ignore", __("Ignore tap"))}
			${button("restore", __("Bring tap back"))}
			${button("add", __("Add missing tap"))}
			${this.mirrored_taps().length ? button("claim", __("Take over this punch")) : ""}
			${this.duplicate_rows().length ? button("dedupe", __("Remove duplicate row")) : ""}
			${this.last_fix ? button("undo", __("Undo last fix")) : ""}
		</div>
		<div class="text-muted small mt-2">
			${__("Hours and overtime are recomputed from the taps; they are never typed here.")}
		</div>`;
	}

	// --- actions --------------------------------------------------------------

	act(action) {
		const run = {
			rebuild: () => this.rebuild(),
			pair: () => this.pair(),
			move: () => this.move(),
			ignore: () => this.ignore(),
			restore: () => this.restore(),
			add: () => this.add(),
			claim: () => this.claim(),
			dedupe: () => this.dedupe(),
			undo: () => this.undo(),
		}[action];
		console.info("[FixDay] action", action);
		return run ? run() : undefined;
	}

	picked(count, message) {
		const taps = Array.from(this.selection);
		if (taps.length !== count) {
			frappe.msgprint(message);
			return null;
		}
		return taps;
	}

	pair() {
		const taps = this.picked(2, __("Tick exactly two taps to pair them as one session."));
		if (!taps) return;
		return this.ask(__("Pair these two taps"), [], (values) =>
			this.run("pair_taps", { a: taps[0], b: taps[1], reason: values.reason })
		);
	}

	move() {
		const taps = this.picked(1, __("Tick exactly one tap to move."));
		if (!taps) return;
		return this.ask(
			__("Move this tap"),
			[
				{ fieldname: "shift", label: __("Shift"), fieldtype: "Link", options: "Shift Type" },
				{ fieldname: "day", label: __("Shift Day"), fieldtype: "Date" },
			],
			(values) =>
				this.run("move_tap", {
					tap: taps[0],
					shift: values.shift,
					day: values.day,
					reason: values.reason,
				})
		);
	}

	// Offered only on a day that actually has more than one live row. The server
	// decides WHICH row may go — it keeps the row the punches are linked to,
	// the same rule the automatic resolver uses — so this only has to ask which
	// one HR means.
	duplicate_rows() {
		const rows = (this.day && this.day.attendance) || [];
		return rows.length > 1 ? rows : [];
	}

	// One press instead of five dialogs. It asks the server what it WOULD do,
	// shows that in sentences, takes one reason, and applies the lot. The five
	// single actions below it are untouched: this refuses any day whose evidence
	// it cannot read, and then they are how HR fixes it.
	rebuild() {
		return fd_call(FD_API + "plan_day", { employee: this.employee, date: this.date }).then((plan) => {
			if (!plan) return null;
			if (plan.blocked) {
				frappe.msgprint({ title: __("This day is not mine to fix"), message: fd_escape(plan.blocked) });
				return null;
			}
			if (plan.refusal) {
				frappe.msgprint({
					title: __("I cannot read this day"),
					indicator: "orange",
					message: `${fd_escape(plan.refusal)}<br><br>${__(
						"Use the buttons below to correct the taps by hand."
					)}`,
				});
				return null;
			}
			return this.ask(
				__("Rebuild this day"),
				[{ fieldtype: "HTML", fieldname: "plan", options: this.plan_html(plan) }],
				(values) =>
					this.run("rebuild_day", {
						employee: this.employee,
						date: this.date,
						reason: values.reason,
					})
			);
		});
	}

	// The plan in words, before anything is written. Every tap it will drop is
	// named here, and so is every long gap that dropping one leaves behind —
	// that sight IS the safeguard for the rule (owner, 17 Sep 2026).
	plan_html(plan) {
		const item = (text) => `<li>${text}</li>`;
		const lines = [];
		for (const row of plan.cancel || []) {
			lines.push(
				item(
					__("Cancel {0} · {1} — {2}", [
						fd_escape(row.name),
						fd_escape(row.shift || __("no shift")),
						fd_escape(row.why),
					])
				)
			);
		}
		if (plan.session) {
			lines.push(
				item(
					__("Keep {0} in and {1} out as this day's session", [
						fd_clock(plan.session.in.time),
						fd_clock(plan.session.out.time),
					])
				)
			);
		}
		for (const row of plan.relabel || []) {
			lines.push(
				item(
					__("Relabel {0} from {1} to {2} — it is the tap that {3} this day", [
						fd_clock(row.time),
						fd_escape(row.from || "—"),
						fd_escape(row.to),
						row.to === "IN" ? __("opens") : __("closes"),
					])
				)
			);
		}
		for (const tap of plan.drop || []) {
			lines.push(
				item(
					__("Ignore {0} {1} — {2}", [
						fd_clock(tap.time),
						fd_escape(tap.log_type || "—"),
						fd_escape(tap.why),
					])
				)
			);
		}
		const notes = (plan.notes || [])
			.map((note) => `<div class="alert alert-warning py-1 my-1">${fd_escape(note)}</div>`)
			.join("");
		return `<div class="mb-2"><b>${__("This is what I will do")}</b></div>
			<ul>${lines.join("")}</ul>
			${notes}
			<div class="text-muted small">
				${__("Hours and overtime are recomputed from what is left; nothing is typed.")}
			</div>`;
	}

	mirrored_taps() {
		return (this.day && this.day.taps ? this.day.taps : []).filter((tap) => tap.mirrored);
	}

	// The punch the old system sent. Until this site owns it, Fix Day refuses it
	// and the hourly job does not even read it — so its day cannot be fixed at
	// all. Offered only when the day actually holds one.
	claim() {
		const ticked = this.selection;
		const mine = this.mirrored_taps().filter((tap) => ticked.has(tap.name));
		if (mine.length !== 1) {
			frappe.msgprint(__("Tick exactly one punch that came from the other site."));
			return;
		}
		const tap = mine[0];
		return this.ask(
			__("Take over {0} {1}?", [fd_clock(tap.time), fd_escape(tap.log_type || "")]),
			[
				{
					fieldtype: "HTML",
					fieldname: "what",
					options: `<div class="mb-2">${__(
						"This punch belongs to the site that recorded it, so nothing here reads it. " +
							"Taking it over makes it this site's: the day can then be rebuilt from it. " +
							"Nothing the device recorded changes, and the undo gives it back."
					)}</div>`,
				},
			],
			(values) => this.run("claim_tap", { tap: tap.name, reason: values.reason })
		);
	}

	dedupe() {
		const rows = this.duplicate_rows();
		if (!rows.length) {
			frappe.msgprint(__("This day has only one attendance row."));
			return;
		}
		return this.ask(
			__("Remove a duplicate attendance row"),
			[
				{
					fieldname: "attendance",
					label: __("Row to cancel"),
					fieldtype: "Select",
					reqd: 1,
					options: rows
						.map((row) => `${row.name} — ${row.shift || __("no shift")} — ${row.status || "—"}`)
						.join("\n"),
				},
			],
			(values) =>
				this.run("remove_duplicate_row", {
					attendance: String(values.attendance).split(" — ")[0],
					reason: values.reason,
				})
		);
	}

	ignore() {
		const taps = this.picked(1, __("Tick exactly one tap to ignore."));
		if (!taps) return;
		return this.ask(__("Ignore this tap"), [], (values) =>
			this.run("ignore_tap", { tap: taps[0], reason: values.reason })
		);
	}

	restore() {
		const taps = this.picked(1, __("Tick exactly one tap to bring back."));
		if (!taps) return;
		return this.ask(__("Bring this tap back"), [], (values) =>
			this.run("restore_tap", { tap: taps[0], reason: values.reason })
		);
	}

	add() {
		return this.ask(
			__("Add a missing tap"),
			[
				{
					fieldname: "moment",
					label: __("Time"),
					fieldtype: "Datetime",
					reqd: 1,
					default: `${this.date} 09:00:00`,
				},
				{
					fieldname: "log_type",
					label: __("Type"),
					fieldtype: "Select",
					options: "IN\nOUT",
					reqd: 1,
				},
			],
			(values) =>
				this.run("add_tap", {
					employee: this.employee,
					moment: values.moment,
					log_type: values.log_type,
					reason: values.reason,
				})
		);
	}

	undo() {
		if (!this.last_fix) return frappe.msgprint(__("There is no fix from this screen to undo."));
		const fix = this.last_fix;
		return new Promise((resolve) => {
			frappe.confirm(
				__("Undo {0}? The taps go back exactly as they were and the day is rebuilt.", [fix]),
				() => resolve(this.run("undo_fix", { log_entry: fix })),
				() => resolve()
			);
		});
	}

	// Every action states a reason; it is recorded on the tap and in the fix log.
	ask(title, fields, then) {
		const dialog = new frappe.ui.Dialog({
			title,
			fields: fields.concat([
				{ fieldname: "reason", label: __("Reason"), fieldtype: "Small Text", reqd: 1 },
			]),
			primary_action_label: __("Apply"),
			primary_action: (values) => {
				dialog.hide();
				return then(values);
			},
		});
		dialog.show();
		return dialog;
	}

	run(method, args) {
		return fd_call(FD_API + method, args).then((answer) => {
			if (!answer || !answer.ok) return null;
			this.last_fix = answer.log || this.last_fix;
			this.show_change(answer);
			return this.reload().then(() => answer);
		});
	}

	show_change(answer) {
		const before = (answer.before && answer.before.days) || {};
		const after = (answer.after && answer.after.days) || {};
		const lines = Object.keys(after).map(
			(day) =>
				`<li><b>${fd_escape(day)}</b><br>
					${__("Before")}: ${fd_day_lines(before[day])}<br>
					${__("After")}: ${fd_day_lines(after[day])}</li>`
		);
		// The day is rebuilt from its punches by the server, and sometimes it
		// cannot be: a day carrying two attendance rows comes back exactly as it
		// went in. Saying "rebuilt" over an unchanged day is how a no-op read as
		// a success for a week (owner, 17 Sep 2026, Norazlin 4 Sep).
		const changed = Object.keys(after).some(
			(day) => fd_day_lines(before[day]) !== fd_day_lines(after[day])
		);
		// The engine answers per day, and "held" is an answer: the never-worse
		// guard rolled the rebuild back, or a protection refused the day. Its
		// sentence is the only thing that explains a day that did not move, so
		// it is printed rather than left in the console.
		const held = Object.entries(answer.rebuild || {})
			.filter(([, verdict]) => verdict && verdict.action === "held")
			.map(
				([day, verdict]) =>
					`<div class="alert alert-warning py-1 my-1">${__("{0}: {1}", [
						fd_escape(day),
						fd_escape(verdict.detail || __("the engine held this day")),
					])}</div>`
			)
			.join("");
		console.info("[FixDay] fixed", answer.log, "changed:", changed, before, after);
		frappe.msgprint({
			title: changed ? __("The day was rebuilt") : __("The day came back unchanged"),
			indicator: changed ? "green" : "orange",
			message: `${held}<ul>${lines.join("")}</ul>`,
		});
	}
}

// HR Fix Days — one employee, a range of days, one shift.
//
// The owner's three steps (21 Sep 2026): tick the punches, choose the shift,
// Apply. Nothing is written until a PREVIEW of the same inputs has been seen:
// the server answers dry_run=1 with what it would do to every day, the table
// shows it, and only then does Apply send dry_run=0 with the reason. Changing
// any field throws the preview away. No hours, no overtime, no status: the
// shift is evidence, the engine recomputes the rest.
class FixDaysDialog {
	constructor({ employee, employee_name, from_date, to_date, on_change }) {
		this.employee = employee;
		this.employee_name = employee_name;
		this.from_date = from_date;
		this.to_date = to_date;
		this.on_change = on_change;
		this.preview = null;
	}

	show() {
		const invalidate = () => this.invalidate();
		this.dialog = new frappe.ui.Dialog({
			title: __("Fix days"),
			size: "extra-large",
			fields: [
				{
					fieldname: "employee",
					label: __("Employee"),
					fieldtype: "Link",
					options: "Employee",
					default: this.employee,
					read_only: 1,
				},
				{
					fieldname: "employee_name",
					label: __("Name"),
					fieldtype: "Data",
					default: this.employee_name,
					read_only: 1,
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "from_date",
					label: __("From"),
					fieldtype: "Date",
					default: this.from_date,
					reqd: 1,
					onchange: invalidate,
				},
				{
					fieldname: "to_date",
					label: __("To"),
					fieldtype: "Date",
					default: this.to_date,
					reqd: 1,
					onchange: invalidate,
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "shift",
					label: __("Shift"),
					fieldtype: "Link",
					options: "Shift Type",
					description: __(
						"applies to every punch in these days, IN and OUT alike; empty = the roster"
					),
					onchange: invalidate,
				},
				{ fieldname: "reason", label: __("Reason"), fieldtype: "Small Text", reqd: 1 },
				{ fieldtype: "Section Break" },
				{ fieldname: "days", fieldtype: "HTML" },
			],
			primary_action_label: __("Apply"),
			primary_action: () => this.apply(),
			secondary_action_label: __("Preview"),
			secondary_action: () => this.preview_days(),
		});
		this.dialog.show();
		this.invalidate();
		console.info("[FixDays] opened", this.employee, this.from_date, "to", this.to_date);
		return this.dialog;
	}

	inputs() {
		const dialog = this.dialog;
		return {
			employee: this.employee,
			from_date: dialog.get_value("from_date"),
			to_date: dialog.get_value("to_date"),
			shift: dialog.get_value("shift") || null,
		};
	}

	key() {
		return JSON.stringify(this.inputs());
	}

	// A preview belongs to the inputs it was made for and to nothing else.
	invalidate() {
		this.preview = null;
		this.dialog.disable_primary_action();
		this.dialog.fields_dict.days.$wrapper.html(
			`<div class="text-muted small">${__("Press Preview to see what each day will become.")}</div>`
		);
	}

	preview_days() {
		const key = this.key();
		console.info("[FixDays] preview", key);
		return this.run("fix_days", Object.assign({ dry_run: 1 }, this.inputs())).then((answer) => {
			if (!answer || !answer.ok) return null;
			this.preview = { key, answer };
			this.render(answer, false);
			this.dialog.enable_primary_action();
			return answer;
		});
	}

	apply() {
		const reason = this.dialog.get_value("reason");
		if (!this.preview || this.preview.key !== this.key()) {
			frappe.msgprint(__("Preview first: the inputs changed since the last preview."));
			return Promise.resolve(null);
		}
		if (!reason) {
			frappe.msgprint(__("Say why: the reason goes on every punch and in the fix log."));
			return Promise.resolve(null);
		}
		const totals = this.preview.answer.totals || {};
		return new Promise((resolve) => {
			frappe.confirm(
				__("Rebuild {0} days, cancel {1} rows?", [totals.rebuilt || 0, totals.cancelled || 0]),
				() => resolve(this.write(reason)),
				() => resolve(null)
			);
		});
	}

	write(reason) {
		return this.run("fix_days", Object.assign({ dry_run: 0, reason }, this.inputs())).then((answer) => {
			if (!answer || !answer.ok) return null;
			console.info("[FixDays] applied", answer.totals);
			this.preview = null;
			this.dialog.disable_primary_action();
			this.render(answer, true);
			if (this.on_change) this.on_change();
			return answer;
		});
	}

	undo(log) {
		console.info("[FixDays] undo", log);
		return this.run("undo_fix", { log_entry: log }).then((answer) => {
			if (!answer || !answer.ok) return null;
			this.dialog.fields_dict.days.$wrapper
				.find(`[data-fd-undo="${log}"]`)
				.replaceWith(`<span class="text-muted">${__("undone")}</span>`);
			if (this.on_change) this.on_change();
			return answer;
		});
	}

	run(method, args) {
		return fd_call(FD_API + method, args);
	}

	// --- painting -------------------------------------------------------------

	tap_text(tap) {
		const before = fd_escape((tap.before && tap.before.shift) || "—");
		const after = fd_escape((tap.after && tap.after.shift) || "—");
		const head = `${fd_escape(tap.log_type || "—")} ${fd_clock(tap.time)}`;
		return tap.changed ? `${head} ${before} → <b>${after}</b>` : `${head} ${before}`;
	}

	cancel_text(row) {
		const hr = row.marked_by_hr ? " " + __("(HR)") : "";
		return `${fd_escape(row.status || "—")} ${fd_escape(row.hours)} h${hr}`;
	}

	day_row(day, applied) {
		const blocked = !!day.blocked;
		const result = blocked
			? `<span class="indicator-pill orange">${fd_escape(day.blocked)}</span>`
			: fd_escape(day.result || "—");
		const undo =
			applied && day.log && !blocked
				? ` <a href="#" data-fd-undo="${fd_escape(day.log)}">${__("Undo")}</a>`
				: "";
		const taps = (day.taps || []).map((tap) => this.tap_text(tap)).join("<br>");
		const cancels = (day.rows_to_cancel || []).map((row) => this.cancel_text(row)).join("<br>");
		const noise = (day.noise || [])
			.map((tap) => `${fd_escape(tap.name)}: ${fd_escape(tap.why)}`)
			.join("<br>");
		return `<tr class="${blocked ? "table-warning" : ""}">
			<td>${fd_escape(day.date)}</td>
			<td>${taps || "—"}</td>
			<td>${cancels || "—"}</td>
			<td>${noise || "—"}</td>
			<td>${result}${undo}</td>
		</tr>`;
	}

	render(answer, applied) {
		const t = answer.totals || {};
		const totals = __(
			"{0} days · {1} rebuilt · {2} left open · {3} blocked · {4} punches restamped · {5} noise · {6} rows cancelled",
			[
				fd_escape(t.days || 0),
				fd_escape(t.rebuilt || 0),
				fd_escape(t.open || 0),
				fd_escape(t.blocked || 0),
				fd_escape(t.restamped || 0),
				fd_escape(t.noise || 0),
				fd_escape(t.cancelled || 0),
			]
		);
		const title = applied ? __("Done") : __("Preview — nothing written yet");
		const wrapper = this.dialog.fields_dict.days.$wrapper;
		wrapper.html(`<div class="mb-2"><b>${title}</b> <span class="text-muted">— ${totals}</span></div>
			<table class="table table-bordered table-sm">
				<thead><tr>
					<th>${__("Day")}</th><th>${__("Punches")}</th><th>${__("Rows to cancel")}</th>
					<th>${__("Noise")}</th><th>${__("Result")}</th>
				</tr></thead>
				<tbody>${(answer.days || []).map((day) => this.day_row(day, applied)).join("")}</tbody>
			</table>`);
		wrapper.off("click.fixdays").on("click.fixdays", "[data-fd-undo]", (event) => {
			if (event.preventDefault) event.preventDefault();
			return this.undo(event.currentTarget.getAttribute("data-fd-undo"));
		});
	}
}

hrms.fix_day.enabled = fd_enabled;

hrms.fix_day.open = function (options) {
	if (!fd_enabled()) {
		frappe.msgprint(__("Only HR can fix a day."));
		return null;
	}
	const screen = new FixDayScreen(options || {});
	screen.show();
	return screen;
};

// Employee Checkin list: tick the taps of ONE employee-day and fix that day.
hrms.fix_day.from_taps = function (listview) {
	const names = (listview.get_checked_items(true) || []).filter(Boolean);
	if (!names.length) {
		frappe.msgprint(__("Tick the taps of the day you want to fix."));
		return Promise.resolve(null);
	}
	return Promise.resolve(
		frappe.db.get_list("Employee Checkin", {
			filters: { name: ["in", names] },
			fields: ["name", "employee", "shift_start", "time", "shift"],
			limit: names.length,
		})
	).then((rows) => {
		const employees = new Set((rows || []).map((row) => row.employee));
		if (employees.size !== 1) {
			frappe.msgprint(__("Tick taps of one person."));
			return null;
		}
		// A shift that runs past midnight puts ONE session on two calendar
		// dates: the IN on the 3rd, its OUT at 01:04 on the 4th. That is the
		// commonest broken day here, not a mis-tick to refuse (owner, 18 Sep
		// 2026, having ticked exactly that pair: "now i cant do much").
		//
		// The day to open is the day HR has to act ON. A STRANDED tap — one with
		// no shift — is the one that needs moving, and it exists only on its own
		// date; open there. With nothing stranded, the earliest ticked day is the
		// day the session belongs to.
		const dated = (rows || []).map((row) => ({
			day: String(row.shift_start || row.time).slice(0, 10),
			stranded: !row.shift,
		}));
		const stranded = dated.filter((row) => row.stranded).map((row) => row.day);
		const days = Array.from(new Set(dated.map((row) => row.day))).sort();
		if (!days.length) {
			frappe.msgprint(__("Tick the taps of the day you want to fix."));
			return null;
		}
		const date = stranded.length ? stranded.sort()[0] : days[0];
		if (days.length > 1) {
			frappe.show_alert({
				message: __("Ticked taps span {0} days; opening {1}.", [days.length, date]),
				indicator: "blue",
			});
		}
		return hrms.fix_day.open({
			employee: Array.from(employees)[0],
			date,
			on_close: () => listview.refresh(),
		});
	});
};

// Employee Checkin list: tick the taps of ONE employee over any days, choose
// the shift they all belong to, preview, apply.
hrms.fix_day.fix_days_from_taps = function (listview) {
	if (!fd_enabled()) {
		frappe.msgprint(__("Only HR can fix a day."));
		return Promise.resolve(null);
	}
	const names = (listview.get_checked_items(true) || []).filter(Boolean);
	if (!names.length) {
		frappe.msgprint(__("Tick the taps of the days you want to fix."));
		return Promise.resolve(null);
	}
	return Promise.resolve(
		frappe.db.get_list("Employee Checkin", {
			filters: { name: ["in", names] },
			fields: ["name", "employee", "employee_name", "shift_start", "time"],
			limit: names.length,
		})
	).then((rows) => {
		const employees = new Set((rows || []).map((row) => row.employee));
		if (employees.size !== 1) {
			frappe.msgprint(__("Tick taps of one person."));
			return null;
		}
		const days = rows.map((row) => String(row.shift_start || row.time).slice(0, 10)).sort();
		const dialog = new FixDaysDialog({
			employee: rows[0].employee,
			employee_name: rows[0].employee_name,
			from_date: days[0],
			to_date: days[days.length - 1],
			on_change: () => listview.refresh(),
		});
		dialog.show();
		return dialog;
	});
};

// The list entry points themselves are registered by each doctype's own list
// script (employee_checkin_list.js), which Desk loads after
// this bundle. Assigning frappe.listview_settings here as well cost HR the
// button for a week: the later assignment simply replaced this one, and the
// chain this file tried to keep (__fd_previous_onload) was never set by anyone.
// One owner per doctype; this bundle owns the screen, not the page.
