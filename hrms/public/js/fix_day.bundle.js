// Copyright (c) 2026, Nastyworldwide-Dev and contributors
// License: GNU General Public License v3. See license.txt

// HR Fix attendance — one employee, the days HR ticked.
//
// Owner rule (16 Sep 2026): HR corrects the EVIDENCE, never the result. This
// dialog shows every punch of the day; a tick means "this punch counts", the
// type cell flips IN/OUT, one Shift box applies to the ticked pair. Unticked
// punches are deleted (the fix log keeps a copy; Undo brings them back). It has
// NO hours field and NO status field on purpose: the engine recomputes hours,
// break, the OT ladder and claimability, and the After line under the table is
// worked out here from the ticks alone so HR sees the row before it is written.
// Owner, 21 Sep 2026: keep the compact dialog, one button, "Save & rebuild".
//
// Loaded at boot (hooks.py app_include_js). Its only door is the
// "Fix attendance" button on the Employee Checkin list (the tool lives on the
// punches page only; the Attendance list and the two reports link there with
// "Punches").
//
// Tests: hrms/hr/doctype/employee_checkin/employee_checkin_list.test.js,
//        hrms/tests/test_fix_day_screen.py

frappe.provide("hrms.fix_day");

const FD_API = "hrms.api.attendance_fix_day.";
const FD_HR_ROLES = ["HR User", "HR Manager", "System Manager"];
//: two taps wider apart than this are not one session (owner rule, 16 Sep 2026)
const FD_MAX_PAIR_HOURS = 20;
//: a punch the engine does not read; shown greyed, a tick restores it (G9)
const FD_HIDDEN_STATES = ["skipped", "rejected"];
const FD_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const FD_DAY_MS = 86400000;

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

// "2026-08-27" → "27 Aug": the day a row lands on, the way HR says it
function fd_day_label(date) {
	const match = String(date || "").match(/^(\d{4})-(\d\d)-(\d\d)/);
	return match ? `${Number(match[3])} ${FD_MONTHS[Number(match[2]) - 1]}` : fd_escape(date);
}

// a Date → its local calendar day "2026-08-27"
function fd_date_of(when) {
	return new Date(when.getTime() - when.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

// "27 Aug" when this punch is NOT on the day being fixed, else "". A shift that
// runs past midnight puts its closing punch on the next calendar date, and the
// dialog lists it under that day's own punches.
function fd_other_day(time, date) {
	const on = String(time || "").slice(0, 10);
	return on && date && on !== String(date) ? fd_day_label(on) : "";
}

// a punch's moment: its own datetime, or the clock HR typed on the day being fixed
function fd_when(row, date) {
	return new Date(row.time ? String(row.time).replace(" ", "T") : `${date}T${row.clock}:00`);
}

// a planned punch {row, at} → "21:00"
function fd_at(t) {
	return fd_clock(t.at.toTimeString());
}

// what save_day is told about a planned punch: the server's name, or the clock
function fd_ref(t) {
	return t ? (t.row.is_new ? { time: t.row.clock } : t.row.name) : null;
}

// One Attendance row in words: hours and overtime are SHOWN, never sent back.
// Leads with NAME and SHIFT, how HR matches it to the list (owner, 17 Sep 2026).
function fd_row_line(row) {
	// what HR reads, no record ids (owner, 21 Sep 2026): status, shift, clocks, hours
	const cells = [row.status || "—", row.shift || __("no shift")].map(fd_escape);
	cells.push(fd_clock(row.in_time), fd_clock(row.out_time), fd_escape(row.hours));
	const ot = fd_escape(row.overtime);
	return __("{0} · {1} · {2} → {3} · {4} h", cells) + (row.overtime ? __(" · {0} h OT", [ot]) : "");
}

function fd_button(action, label, klass) {
	return `<button class="btn btn-sm mr-2 ${klass || "btn-default"}" data-fd-action="${action}">${label}</button>`;
}

function fd_day_lines(rows, joiner) {
	if (!rows || !rows.length) return __("no attendance row");
	return rows.map(fd_row_line).join(joiner || "<br>");
}

function fd_call(method, args) {
	console.info("[FixDay] call", method);
	return Promise.resolve(
		frappe.call({ method, args, freeze: true, freeze_message: __("Fixing the day...") })
	).then((answer) => (answer && answer.message) || null);
}

// The ticked punches, in time order, as sessions — or the one reason they are
// not. Pure: this is the whole local rule, and the After line is read off it.
//   G4 not 1 IN + 1 OUT per session · G6 IN after OUT · G3 pair > 20 h ·
//   G10 sessions overlap · G5 one tick needs "Leave open"
function fd_plan(rows, date, leave_open) {
	const ticked = rows.filter((row) => row.counts).map((row) => ({ row, at: fd_when(row, date) }));
	console.info("[FixDay] plan", date, ticked.length, "ticked");
	if (!ticked.length) return { error: __("Nothing ticked: tick the IN and the OUT that count.") };
	// a new OUT typed as a clock earlier than the latest ticked IN is the next morning
	const ins_at = ticked.filter((t) => t.row.log_type === "IN").map((t) => t.at.getTime());
	const last_in = ins_at.length ? Math.max(...ins_at) : -Infinity;
	for (const t of ticked) {
		if (t.row.is_new && t.row.log_type === "OUT" && t.at.getTime() < last_in) {
			t.at = new Date(t.at.getTime() + FD_DAY_MS);
		}
	}
	ticked.sort((a, b) => a.at - b.at);
	if (ticked.length === 1) {
		if (!leave_open) return { error: __("one punch ticked: add its pair or Leave open (no row)"), lone: true };
		const t = ticked[0];
		return { open: t, pairs: [t.row.log_type === "IN" ? { in: t, out: null } : { in: null, out: t }] };
	}
	const ins = ins_at.length;
	const outs = ticked.length - ins;
	if (ins !== outs) {
		return { error: __("Tick 1 IN and 1 OUT for each session (ticked: {0} IN, {1} OUT)", [ins, outs]) };
	}
	const pairs = [];
	let open = null;
	for (const t of ticked) {
		if (t.row.log_type === "IN") {
			if (open) {
				return { error: __("sessions overlap: {0} IN opens before {1} IN is closed", [fd_at(t), fd_at(open)]) };
			}
			open = t;
			continue;
		}
		if (!open) {
			const next_in = ticked.find((u) => u.row.log_type === "IN" && u.at > t.at);
			return { error: __("IN after OUT: {0} IN comes after {1} OUT", [fd_at(next_in), fd_at(t)]) };
		}
		const hours = (t.at - open.at) / 3600000;
		if (hours > FD_MAX_PAIR_HOURS) return { error: __("this pair is {0} h long", [hours.toFixed(1)]) };
		pairs.push({ in: open, out: t, hours });
		open = null;
	}
	return { pairs, hours: pairs.reduce((sum, pair) => sum + pair.hours, 0) };
}

class FixDayScreen {
	// `dates`: the ticked days of ONE employee, earliest first. The dialog opens
	// on the first and "Next day →" walks the rest; only the days HR has SEEN
	// are saved (G15).
	constructor({ employee, date, dates, on_change }) {
		this.employee = employee;
		this.dates = (dates && dates.length ? dates : [date]).slice().sort();
		this.index = 0;
		this.on_change = on_change;
		this.state = {};
		this.saved = [];
		this.syncing = false;
	}

	get date() {
		return this.dates[this.index];
	}

	get current() {
		return this.state[this.date];
	}

	show() {
		this.dialog = new frappe.ui.Dialog({
			title: __("Fix attendance"),
			size: "large",
			fields: [
				{ fieldname: "screen", fieldtype: "HTML" },
				{
					fieldname: "shift",
					label: __("Shift"),
					fieldtype: "Link",
					options: "Shift Type",
					description: __("applies to the ticked pair; the landing day follows it"),
					onchange: () => this.shift_changed(),
				},
				{ fieldname: "summary", fieldtype: "HTML" },
				{
					fieldname: "reason",
					label: __("Reason"),
					fieldtype: "Small Text",
					reqd: 1,
					description: __("goes on every punch and in the fix log"),
				},
			],
			primary_action_label: __("Save & rebuild"),
			primary_action: () => this.save(),
			secondary_action_label: __("Close"),
			secondary_action: () => this.close(),
		});
		this.dialog.show();
		console.info("[FixDay] opened", this.employee, this.dates);
		return this.load(this.date);
	}

	close() {
		this.dialog.hide();
	}

	// --- state ----------------------------------------------------------------

	load(date) {
		if (this.state[date]) {
			this.render();
			return Promise.resolve(this.state[date].day);
		}
		return fd_call(FD_API + "get_day", { employee: this.employee, date }).then((day) => {
			this.state[date] = this.fresh_state(day || {});
			this.render();
			return day;
		});
	}

	// The engine's own pair is the pre-tick (a suggestion: HR's ticks replace
	// it, G1); without one, the punches that count today. A punch from an
	// approved request is ticked and locked (G7); a hidden one is unticked
	// and greyed (G9).
	fresh_state(day) {
		// `get_day` marks the engine's pair PER TAP: `suggested` = "IN" / "OUT"
		// on the two taps it would read the day from (verifier, 21 Sep 2026).
		const from_engine = (day.taps || []).some((tap) => tap.suggested);
		// ...and says WHY when it marked none. A day the engine refuses is the
		// only kind HR opens this for, and the old fallback ticked every counted
		// punch on it: Adam Daniel's 18 August opened as 3 IN + 1 OUT, which the
		// dialog then refused itself, with Save & rebuild dead (22 Sep 2026).
		// Nothing pre-ticked, the reason on screen, HR ticks the real pair.
		const unreadable = !from_engine && Boolean(day.suggestion_refusal);
		const rows = (day.taps || []).map((tap) => {
			const locked = Boolean(tap.linked_request);
			const hidden = FD_HIDDEN_STATES.includes(tap.state);
			const counts = unreadable ? false : from_engine ? Boolean(tap.suggested) : Boolean(tap.counted);
			return {
				name: tap.name,
				time: tap.time,
				clock: fd_clock(tap.time),
				// A punch of THIS shift-day may land the next calendar morning
				// (a 7PM-3.30AM shift). Shown bare it read as a twin of the
				// previous morning's punch 24 h earlier (22 Sep 2026).
				day_label: fd_other_day(tap.time, day.date),
				// the engine's reading of the tap (IN/OUT) is the pre-applied label;
				// the device's label stays visible through the flip (G1)
				log_type: (from_engine && tap.suggested) || tap.log_type || "IN",
				shift: tap.shift,
				state: tap.state,
				device_id: tap.device_id,
				why: tap.why || tap.state,
				linked_request: tap.linked_request || null,
				locked,
				hidden,
				counts: locked || (!hidden && counts),
				is_new: false,
			};
		});
		console.info("[FixDay] day", day.date, rows.length, "punch(es), pre-ticked:", rows.filter((r) => r.counts).length);
		return { day, rows, leave_open: false, shift: this.default_shift(rows), by_hand: false, added: 0 };
	}

	default_shift(rows) {
		const first_in = rows.find((row) => row.counts && row.log_type === "IN");
		return (first_in && first_in.shift) || null;
	}

	visited() {
		return this.dates.filter((date) => this.state[date]);
	}

	plan(date) {
		const state = this.state[date];
		if (state.day.blocked) return { error: state.day.blocked };
		return fd_plan(state.rows, date, state.leave_open);
	}

	// Unticked punches the server knows. Not a locked one (G7: kept, it came
	// from an approved request) and not one that was hidden already.
	to_delete(state) {
		return state.rows.filter((row) => !row.is_new && !row.counts && !row.locked && !row.hidden);
	}

	// --- painting -------------------------------------------------------------

	render() {
		const state = this.current;
		const wrapper = this.dialog.fields_dict.screen.$wrapper;
		wrapper.html(this.header_html(state.day) + this.taps_html(state) + this.buttons_html(state));
		wrapper
			.off("click.fixday")
			.on("click.fixday", "[data-fd-action]", (event) =>
				this.act(event.currentTarget.getAttribute("data-fd-action"))
			)
			.on("click.fixday", "[data-fd-flip]", (event) =>
				this.flip(event.currentTarget.getAttribute("data-fd-flip"))
			)
			.on("click.fixday", "[data-fd-nav]", (event) => {
				if (event.preventDefault) event.preventDefault();
				return this.nav(event.currentTarget.getAttribute("data-fd-nav"));
			});
		wrapper.off("change.fixday").on("change.fixday", "[data-fd-tick]", (event) =>
			this.tick(event.currentTarget.getAttribute("data-fd-tick"), Boolean(event.currentTarget.checked))
		);
		this.sync_shift(state.shift);
		this.render_summary();
		this.render_primary();
	}

	header_html(day) {
		const many = this.dates.length > 1;
		const prev = many && this.index > 0 ? `<a href="#" class="mr-3" data-fd-nav="prev">${__("← Prev day")}</a>` : "";
		const next =
			many && this.index < this.dates.length - 1
				? `<a href="#" class="ml-3" data-fd-nav="next">${__("Next day →")}</a>`
				: "";
		const count = many ? ` <span class="text-muted small">(${this.index + 1}/${this.dates.length})</span>` : "";
		return `<div class="mb-3">${prev}<b>${fd_escape(day.employee_name || day.employee)}</b> ·
			${fd_escape(day.date)}${count}${next}</div>`;
	}

	tap_html(row) {
		const checked = row.counts ? " checked" : "";
		const disabled = row.locked ? " disabled" : "";
		const struck = !row.counts && !row.hidden;
		const klass = row.hidden && !row.counts ? "text-muted" : struck ? "fd-struck text-muted" : "";
		const style = struck ? ' style="text-decoration: line-through"' : "";
		const tags = [];
		if (row.locked) tags.push(`<span class="indicator-pill blue">${__("from approved request")}</span>`);
		if (row.is_new) tags.push(`<span class="indicator-pill green">${__("new")}</span>`);
		if (row.hidden) tags.push(`<span class="text-muted small">${__("hidden: {0}", [fd_escape(row.why)])}</span>`);
		return `<tr class="${klass}" data-fd-row="${fd_escape(row.name)}"${style}>
			<td><input type="checkbox" data-fd-tick="${fd_escape(row.name)}"${checked}${disabled}></td>
			<td>${fd_escape(row.clock)}${row.day_label ? ` <span class="text-muted small">${fd_escape(row.day_label)}</span>` : ""}</td>
			<td><button class="btn btn-xs btn-default" data-fd-flip="${fd_escape(row.name)}">${fd_escape(row.log_type)}</button></td>
			<td>${fd_escape(row.shift || "—")}</td>
			<td>${tags.join(" ") || `<span class="text-muted small">${fd_escape(row.state)}</span>`}</td>
			<td class="text-muted small">${fd_escape(row.device_id || "")}</td>
		</tr>`;
	}

	taps_html(state) {
		const rows = state.rows.map((row) => this.tap_html(row)).join("");
		return `<table class="table table-bordered table-sm">
			<thead><tr>
				<th>${__("Counts")}</th><th>${__("Time")}</th><th>${__("Type")}</th>
				<th>${__("Shift")}</th><th>${__("State")}</th><th>${__("Device")}</th>
			</tr></thead>
			<tbody>${rows || `<tr><td colspan="6">${__("No punches on this day.")}</td></tr>`}</tbody>
		</table>`;
	}

	buttons_html(state) {
		const one = state.rows.filter((row) => row.counts).length === 1;
		const open = state.leave_open ? "btn-primary" : "btn-default";
		return `<div class="mb-2">
			${fd_button("add_in", __("+ Add IN"))}
			${fd_button("add_out", __("+ Add OUT"))}
			${one ? fd_button("leave_open", __("Leave open (no row)"), open) : ""}
		</div>`;
	}

	after_line(plan, shift) {
		if (plan.error) return `<div class="text-danger"><b>${fd_escape(plan.error)}</b></div>`;
		if (plan.open) {
			const open = `${fd_at(plan.open)} ${fd_escape(plan.open.row.log_type)} (${shift})`;
			return `<div><b>${__("After")}: ${__("no row (left open)")} · ${open}</b></div>`;
		}
		const first = plan.pairs[0].in;
		const last = plan.pairs[plan.pairs.length - 1].out;
		const n = plan.pairs.length;
		const sessions = n > 1 ? ` (${n === 2 ? __("two sessions, added up") : __("{0} sessions, added up", [n])})` : "";
		const lands = __("lands on {0} ({1})", [fd_day_label(fd_date_of(first.at)), shift]);
		const span = `${fd_at(first)} → ${fd_at(last)} · ${plan.hours.toFixed(1)} h${sessions}`;
		return `<div><b>${__("After")}: ${__("Present")} · ${span} · ${lands}</b></div>`;
	}

	// The After line: the row the ticks make, worked out here. A guard message
	// takes its place and turns Save off. Under it, today's rows in one line.
	render_summary() {
		const state = this.current;
		const plan = this.plan(this.date);
		const deleted = this.to_delete(state).length;
		const line = this.after_line(plan, fd_escape(state.shift || __("no shift")));
		const del = deleted
			? `<div class="text-muted small">${__("{0} punches will be deleted (the fix log keeps a copy; Undo brings them back)", [deleted])}</div>`
			: "";
		const now = `<div class="text-muted small">${__("Now")}: ${fd_day_lines(state.day.attendance, " | ")}</div>`;
		const note = `<div class="text-muted small">${__("Hours and status are recomputed from the ticked punches; they are never typed here.")}</div>`;
		// The engine's own reason for suggesting no pair, above the rest: it is
		// why nothing is ticked, and it tells HR what to look for.
		const why = state.day.suggestion_refusal
			? `<div class="alert alert-warning py-1 my-1">${fd_escape(
					__("The engine could not read this day: {0} Tick the IN and the OUT that count.", [
						state.day.suggestion_refusal,
					])
				)}</div>`
			: "";
		this.dialog.fields_dict.summary.$wrapper.html(why + line + del + now + note);
		if (plan.error) this.dialog.disable_primary_action();
		else this.dialog.enable_primary_action();
	}

	render_primary() {
		const days = this.visited().length;
		const label = days > 1 ? __("Save & rebuild {0} days", [days]) : __("Save & rebuild");
		this.dialog.set_primary_action(label, () => this.save());
	}

	sync_shift(value) {
		this.syncing = true;
		try {
			if (this.dialog.get_value("shift") !== value) this.dialog.set_value("shift", value);
		} finally {
			this.syncing = false;
		}
	}

	// --- what HR does ---------------------------------------------------------

	tick(name, checked) {
		const row = this.current.rows.find((r) => r.name === name);
		if (!row || row.locked) return;
		row.counts = checked;
		this.current.leave_open = false;
		if (!this.current.by_hand) this.current.shift = this.default_shift(this.current.rows);
		console.info("[FixDay] tick", name, checked);
		this.render();
	}

	flip(name) {
		const row = this.current.rows.find((r) => r.name === name);
		if (!row) return;
		row.log_type = row.log_type === "IN" ? "OUT" : "IN";
		if (!this.current.by_hand) this.current.shift = this.default_shift(this.current.rows);
		console.info("[FixDay] flip", name, row.log_type);
		this.render();
	}

	shift_changed() {
		if (this.syncing) return;
		this.current.shift = this.dialog.get_value("shift") || null;
		this.current.by_hand = true;
		console.info("[FixDay] shift by hand", this.date, this.current.shift);
		this.render_summary();
	}

	nav(direction) {
		const index = this.index + (direction === "next" ? 1 : -1);
		if (index < 0 || index >= this.dates.length) return Promise.resolve(null);
		this.index = index;
		console.info("[FixDay] day", this.date);
		return this.load(this.date);
	}

	act(action) {
		const run = {
			add_in: () => this.add("IN"),
			add_out: () => this.add("OUT"),
			leave_open: () => this.leave_open(),
		}[action];
		return run ? run() : undefined;
	}

	leave_open() {
		this.current.leave_open = !this.current.leave_open;
		this.render();
	}

	// A punch the reader missed: one clock, added as a ticked row marked "new".
	add(log_type) {
		return frappe.prompt(
			[{ fieldname: "time", label: __("Time"), fieldtype: "Time", reqd: 1 }],
			(values) => this.add_row(log_type, fd_clock(values.time)),
			__("Add {0}", [log_type]),
			__("Add")
		);
	}

	add_row(log_type, clock) {
		const state = this.current;
		state.added += 1;
		state.rows.push({
			name: `new-${log_type.toLowerCase()}-${state.added}`,
			time: null,
			clock,
			log_type,
			shift: null,
			state: "new",
			device_id: "",
			why: "",
			linked_request: null,
			locked: false,
			hidden: false,
			counts: true,
			is_new: true,
		});
		state.leave_open = false;
		console.info("[FixDay] added", log_type, clock);
		this.render();
	}

	// --- Save & rebuild ---------------------------------------------------------

	args_for(date, reason) {
		const state = this.state[date];
		const plan = this.plan(date);
		const pairs = plan.pairs.map((pair) => ({ in: fd_ref(pair.in), out: fd_ref(pair.out), shift: state.shift }));
		return {
			employee: this.employee,
			date,
			pairs: JSON.stringify(pairs),
			delete: JSON.stringify(this.to_delete(state).map((row) => row.name)),
			reason,
			leave_open: plan.open ? 1 : 0,
			seen_modified: state.day.seen_modified,
		};
	}

	// One save_day per visited day, in order; the first refusal stops the run
	// (the server's message is already on screen). Then Undo takes the primary.
	save() {
		const reason = this.dialog.get_value("reason");
		if (!reason) {
			frappe.msgprint(__("Say why: the reason goes on every punch and in the fix log."));
			return Promise.resolve(null);
		}
		const dates = this.visited();
		for (const date of dates) {
			const plan = this.plan(date);
			if (plan.error) {
				frappe.msgprint(__("{0}: {1}", [fd_escape(date), fd_escape(plan.error)]));
				return Promise.resolve(null);
			}
		}
		console.info("[FixDay] save", dates);
		const results = [];
		return dates
			.reduce((chain, date) => chain.then((ok) => ok && this.save_one(date, reason, results)), Promise.resolve(true))
			.then(() => {
				if (!results.length) return null;
				this.saved = results;
				this.render_results(results);
				this.dialog.set_primary_action(__("Undo"), () => this.undo());
				this.dialog.enable_primary_action();
				if (this.on_change) this.on_change();
				return results;
			});
	}

	save_one(date, reason, results) {
		return fd_call(FD_API + "save_day", this.args_for(date, reason))
			.then((answer) => {
				if (!answer || !answer.ok) return false;
				results.push({ date, answer });
				return true;
			})
			.catch((error) => {
				console.warn("[FixDay] save refused", date, error && error.message);
				return false;
			});
	}

	// The answer per day: the row it made, and the engine's warnings as yellow
	// notes — a warning is not a refusal.
	render_results(results) {
		const html = results.map(({ date, answer }) => this.result_html(date, answer)).join("");
		console.info("[FixDay] saved", results.map((r) => r.answer.log));
		this.dialog.fields_dict.summary.$wrapper.html(html);
	}

	result_html(date, answer) {
		const after = (answer.after && answer.after.days && answer.after.days[date]) || [];
		const held = Object.entries(answer.rebuild || {})
			.filter(([, verdict]) => verdict && verdict.action === "held")
			.map(([, verdict]) => verdict.detail || __("the engine held this day"));
		const warnings = (answer.warnings || [])
			.concat(held)
			.map((text) => `<div class="alert alert-warning py-1 my-1">${fd_escape(text)}</div>`)
			.join("");
		return `<div class="mb-2"><b>${fd_escape(date)}</b> · ${__("rebuilt")} (${fd_escape(answer.log)})<br>
			${__("After")}: ${fd_day_lines(after)}${warnings}</div>`;
	}

	// Undo every save of this dialog, latest first: the punches come back and
	// the rows return; then each day is read again.
	undo() {
		const reason = this.dialog.get_value("reason");
		const logs = this.saved.map((r) => r.answer.log).reverse();
		console.info("[FixDay] undo", logs);
		return logs
			.reduce(
				(chain, log) => chain.then(() => fd_call(FD_API + "undo_fix", { log_entry: log, reason })),
				Promise.resolve()
			)
			.then(() => {
				this.saved = [];
				this.state = {};
				if (this.on_change) this.on_change();
				return this.load(this.date);
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
	return screen.show().then(() => screen);
};

// Employee Checkin list: tick the punches of ONE employee over any days and
// open the dialog on the earliest; "Next day →" walks the rest. A shift that
// runs past midnight puts one session on two calendar dates (the IN on the
// 3rd, its OUT at 01:04 on the 4th), so the day of a punch is its shift's day.
hrms.fix_day.from_taps = function (listview) {
	const names = (listview.get_checked_items(true) || []).filter(Boolean);
	if (!names.length) {
		frappe.msgprint(__("Tick the punches of the day you want to fix."));
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
		const dates = Array.from(
			new Set(rows.map((row) => String(row.shift_start || row.time).slice(0, 10)))
		).sort();
		console.info("[FixDay] from taps", names.length, "punch(es) over", dates);
		return hrms.fix_day.open({
			employee: Array.from(employees)[0],
			dates,
			on_change: () => listview.refresh(),
		});
	});
};

// The list entry point itself is registered by the doctype's own list script
// (employee_checkin_list.js), which Desk loads after this bundle. Assigning
// frappe.listview_settings here as well cost HR the button for a week: the
// later assignment simply replaced this one. One owner per doctype; this
// bundle owns the dialog, not the page.
