// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("HRMS ERP Instance", {
	refresh(frm) {
		if (frm.is_new()) return;

		// BEFORE the `enabled` gate, both of them deliberately.
		//
		// Purge is cleanup for a DECOMMISSIONED instance, and disabling is how
		// you decommission one — so hiding it behind `enabled` hid it in exactly
		// the case it exists for. Observed: an operator had to re-enable a dead
		// instance to clean it up, which is backwards and briefly re-armed the
		// sync client to do it.
		//
		// The scope line has to render for a disabled instance too: the fence
		// still applies while disabled ("Does NOT affect the permission fence"
		// is right there on the Enabled field), so what it resolves to is still
		// the operator's business.
		frm.add_custom_button(__("Purge Mirrored Data"), () => purge_mirror(frm), __("Danger"));

		// The SAFE recovery when a second instance (a cloned dev ERP) has stamped rows
		// that are really live: it deletes nothing, just forgets provenance, so the real
		// source reclaims them on the next full sync. Step 2 of the "Where did this data
		// come from" safe order — a button, because the operator cannot run a console and
		// Purge (right above) is the destructive thing they would reach for instead.
		frm.add_custom_button(__("Release This Instance's Stamp"), () => release_stamp(frm), __("Danger"));

		// Read-only, and OUTSIDE the `enabled` gate for the same reason Purge is:
		// the question "which source do these rows really belong to?" matters
		// most about an instance somebody has just disabled.
		//
		// It exists as a button rather than only `bench execute` because the
		// answer decides whether it is safe to press Purge, and an operator who
		// has to open a shell to find that out will press Purge instead. That is
		// not hypothetical here — it already cost a live record.
		frm.add_custom_button(__("Where Did This Data Come From?"), () => check_sources());

		show_company_scope(frm);

		if (!frm.doc.enabled) return;

		// Ordered as the operator must run them: companies first, because an
		// Employee whose company is absent here is skipped, not written.
		frm.add_custom_button(__("Pull Companies from Source"), () => pull_companies(frm));
		frm.add_custom_button(__("Sync Employee Data"), () => sync_now(frm));
		frm.add_custom_button(__("Check Data Parity"), () => check_parity(frm));
		frm.add_custom_button(__("What Else Is On The Source"), () => survey_source(frm));
		frm.add_custom_button(__("Check Field Completeness"), () => check_field_completeness(frm));
		frm.add_custom_button(__("Review Schema Gaps"), () => review_schema_gaps(frm));
		show_sync_headline(frm);
	},

	companies(frm) {
		// The row count changed, so the effective scope did too.
		show_company_scope(frm);
	},
});

//: canonical gap prefix -> what an operator should read it as
const GAP_KINDS = {
	"field:": __("column the hub does not store"),
	"value:": __("value the hub refuses"),
	"absent:": __("doctype the source does not have"),
	"unmirrored:": __("source data not brought across"),
	"unreadable:": __("source refuses the read"),
};

function describe_gap(key) {
	for (const [prefix, label] of Object.entries(GAP_KINDS)) {
		if (key.startsWith(prefix)) return `${key.slice(prefix.length)} — ${label}`;
	}
	return key;
}

function review_schema_gaps(frm) {
	// One screen, zero typing. The machine already knows every canonical key —
	// readiness reports them — so the operator only supplies the DECISION.
	// Hand-copying keys like value:Employee.performance_band=E3 into the child
	// table was the workflow this replaces: one typo and a ruling never matches
	// its gap, blocking READY while looking done.
	frappe
		.call({
			method: "hrms.sync.parity.cutover_readiness",
			args: { instance_name: frm.doc.name },
		})
		.then((r) => {
			const v = r.message || {};
			const unruled = v.unruled || [];
			const unmet = v.unmet || [];
			if (!unruled.length && !unmet.length) {
				frappe.msgprint({
					title: __("Nothing outstanding"),
					indicator: "green",
					message: __(
						"Every reported schema gap carries a ruling, and none are pending work.",
					),
				});
				return;
			}

			const fields = [];
			if (unmet.length) {
				fields.push({
					fieldtype: "HTML",
					options:
						`<p class="text-muted" style="margin-bottom:0.5em">${__(
							"Ruled, still outstanding — these clear on their own when the gap stops appearing:",
						)}</p>` +
						`<ul style="margin:0 0 0.5em 1em">${unmet
							.map(
								(key) => `<li>${frappe.utils.escape_html(describe_gap(key))}</li>`,
							)
							.join("")}</ul>`,
				});
			}
			unruled.forEach((key, index) => {
				fields.push({
					fieldtype: "Select",
					fieldname: `ruling_${index}`,
					label: describe_gap(key),
					options: [
						"",
						__("Not needed on hub"),
						__("Add before cutover"),
						__("Fix at source"),
					].join("\n"),
				});
			});

			const dialog = new frappe.ui.Dialog({
				title: __("Review Schema Gaps"),
				fields,
				primary_action_label: __("Record Rulings"),
				primary_action(values) {
					// untranslate: the ledger stores the canonical English rulings
					const canonical = {
						[__("Not needed on hub")]: "Not needed on hub",
						[__("Add before cutover")]: "Add before cutover",
						[__("Fix at source")]: "Fix at source",
					};
					let recorded = 0;
					unruled.forEach((key, index) => {
						const choice = canonical[values[`ruling_${index}`]];
						if (!choice) return; // undecided rows stay unruled — deciding later is allowed
						const row = frm.add_child("schema_gap_rulings");
						row.gap = key;
						row.ruling = choice;
						recorded += 1;
					});
					dialog.hide();
					if (!recorded) return;
					frm.refresh_field("schema_gap_rulings");
					frm.save().then(() => {
						console.info(
							"[HRMSERPInstance] recorded",
							recorded,
							"schema gap ruling(s)",
						);
						show_sync_headline(frm); // the READY math may have just changed
					});
				},
			});
			dialog.show();
		})
		.catch((e) => console.warn("[HRMSERPInstance] could not load gaps for review:", e));
}

function show_sync_headline(frm) {
	// set_headline APPENDS — verifica-live 2026-08-18 showed "1 of 4" stacked
	// above "2 of 4" after the second parity check. One standing answer at a
	// time: clear before writing.
	frm.dashboard.clear_headline();
	// "Is it running?" answered on the form itself, not by refreshing the list
	// blind. sync_status was built for exactly this and had no caller. The call
	// fails SILENTLY on purpose: a company-fenced HR user gets a PermissionError
	// from the endpoint (registry actions are hub-wide), and a form that loads
	// fine without a headline beats one that throws on open.
	frappe
		.call({ method: "hrms.sync.runner.sync_status", args: { instance_name: frm.doc.name } })
		.then((r) => {
			const status = r.message || {};
			if (status.run) {
				frm.dashboard.set_headline(
					__("Sync in progress: {0} — the run record updates as it finishes.", [
						`<a href="/app/hrms-sync-run/${encodeURIComponent(
							status.run,
						)}">${frappe.utils.escape_html(status.run)}</a>`,
					]),
				);
			} else if (status.workers === 0) {
				frm.dashboard.set_headline(
					__(
						"No background worker is consuming the {0} queue — a queued sync would never start.",
						[frappe.utils.escape_html(status.queue || "long")],
					),
				);
			} else {
				show_cutover_readiness(frm);
			}
		})
		.catch(() => {});
}

function show_cutover_readiness(frm) {
	// The standing answer to "can we cut over?" — the trailing streak of clean
	// parity checks against the exit criterion. Nothing recorded yet renders
	// nothing: a site that never runs the gate should not see a scary NOT READY.
	frappe
		.call({
			method: "hrms.sync.parity.cutover_readiness",
			args: { instance_name: frm.doc.name },
		})
		.then((r) => {
			const v = r.message || {};
			if (!v.checks_recorded) return;
			const blockers = (v.unruled || []).length + (v.unmet || []).length;
			const label = v.ready
				? __("READY — {0} consecutive clean parity checks (need {1}).", [
						v.consecutive_clean_runs,
						v.required,
					])
				: blockers
					? __(
							"Cutover: {0} of {1} clean checks; {2} schema ruling(s) outstanding — see Schema Gap Rulings below.",
							[v.consecutive_clean_runs, v.required, blockers],
						)
					: __("Cutover: {0} of {1} consecutive clean parity checks.", [
							v.consecutive_clean_runs,
							v.required,
						]);
			frm.dashboard.set_headline(
				`${label} <a href="/app/hrms-parity-check?source_instance=${encodeURIComponent(
					frm.doc.name,
				)}">${__("History")}</a>`,
			);
		})
		.catch(() => {});
}

function survey_source(frm) {
	// Counts every HR doctype the mirror does NOT carry. Turns "should we also
	// bring payroll?" into a row count instead of an argument — a doctype holding
	// nothing is not a gap however important it sounds.
	console.info("[HRMSERPInstance] surveying unmirrored doctypes on", frm.doc.name);
	frappe.call({
		method: "hrms.sync.parity.source_survey",
		args: { instance_name: frm.doc.name },
		freeze: true,
		freeze_message: __("Counting what the source holds…"),
		callback: (r) => report_survey(r.message || {}),
		error: (e) => console.warn("[HRMSERPInstance] survey failed:", e),
	});
}

function check_field_completeness(frm) {
	// Per mirrored employee, per field: what the sync left blank here, and whether
	// the SOURCE has a value. The half-filled-employee answer (missing branch /
	// grade / shift_location) split into the two causes with opposite fixes.
	console.info("[HRMSERPInstance] field completeness against", frm.doc.name);
	frappe.call({
		method: "hrms.sync.parity.field_completeness",
		args: { instance_name: frm.doc.name },
		freeze: true,
		freeze_message: __("Comparing every mirrored field against the source…"),
		callback: (r) => report_field_completeness(r.message || {}),
		error: (e) => console.warn("[HRMSERPInstance] field completeness failed:", e),
	});
}

function report_field_completeness(report) {
	const esc = frappe.utils.escape_html;
	const per_field = report.per_field || {};
	const fields = Object.keys(per_field).sort();
	const sync_total = report.sync_fidelity_gap_total || 0;

	console.info("[HRMSERPInstance] field completeness:", sync_total, "sync-dropped values");

	const rows = fields
		.map((f) => {
			const c = per_field[f];
			return `<tr><td>${esc(f)}</td>
				<td style="text-align:right">${c.empty_here}</td>
				<td style="text-align:right;color:#b45309"><b>${c.filled_on_source}</b></td>
				<td style="text-align:right">${c.empty_both}</td></tr>`;
		})
		.join("");

	frappe.msgprint({
		title: sync_total
			? __("The sync dropped {0} value(s) — a code fix", [sync_total])
			: __("Nothing was dropped by the sync"),
		indicator: sync_total ? "red" : "green",
		message:
			`<p>${__("Checked {0} mirrored {1}.", [
				report.rows_here || 0,
				report.doctype || __("row"),
			])}</p>
			<table class="table table-bordered" style="margin:0">
				<thead><tr>
					<th>${__("Field")}</th>
					<th style="text-align:right">${__("Blank here")}</th>
					<th style="text-align:right">${__("Sync dropped (fix in code)")}</th>
					<th style="text-align:right">${__("Source blank (HR fills)")}</th>
				</tr></thead>
				<tbody>${rows}</tbody>
			</table>
			<p class="text-muted">${__(
				"Amber = the value is on the source but did not cross — send this to the developer. Last column = blank on both sides — only HR can fill it.",
			)}</p>`,
	});
}

function report_survey(report) {
	const esc = frappe.utils.escape_html;
	const gaps = report.has_data || [];

	console.info("[HRMSERPInstance] survey:", gaps.length, "doctype(s) with data not mirrored");

	const rows = gaps
		.map(
			(line) =>
				`<tr><td>${esc(line.doctype)}</td><td style="text-align:right">${
					line.rows
				}</td></tr>`,
		)
		.join("");

	const aside = (label, list) =>
		(list || []).length
			? `<p class="text-muted">${label}: ${list
					.map((x) => esc(x.doctype || x))
					.join(", ")}</p>`
			: "";

	frappe.msgprint({
		title: gaps.length ? __("Not mirrored, and not empty") : __("Nothing left behind"),
		indicator: gaps.length ? "orange" : "green",
		message:
			(gaps.length
				? `<table class="table table-bordered" style="margin:0">
						<thead><tr><th>${__("Doctype")}</th><th style="text-align:right">${__(
							"Rows on source",
						)}</th></tr></thead>
						<tbody>${rows}</tbody>
					</table>
					<p>${__(
						"These exist on the source and are not brought across. Largest first — that is the order worth arguing about.",
					)}</p>`
				: `<p>${__("Every unmirrored doctype checked is empty on the source.")}</p>`) +
			aside(__("Empty over there"), report.empty) +
			aside(__("Not on that source at all"), report.not_on_source) +
			// Not `aside`: it renders names only, and here the name is the least
			// useful half. `source_inventory` has always collected the remote's error
			// per doctype and this dialog dropped it — so "could not read" read as
			// "grant a permission" whether or not a permission was the cause. Advice
			// presented as a diagnosis, with the diagnosis in hand the whole time.
			unreadable_html(report.unreadable),
	});
}

// Each unreadable doctype with what the source actually SAID. A permission is
// the usual cause and not the only one, and the two are only distinguishable
// from the error text.
function unreadable_html(list) {
	if (!(list || []).length) return "";
	console.warn("[HRMSERPInstance] unreadable on source:", list);
	const esc = frappe.utils.escape_html;
	const rows = list
		.map(
			(row) =>
				`<li><b>${esc(row.doctype || row)}</b> — ${esc(
					row.error || __("no reason given"),
				)}</li>`,
		)
		.join("");
	return `<p class="text-muted">${__("Could not read — the source answered:")}</p>
		<ul class="text-muted" style="margin:0 0 0 1em">${rows}</ul>`;
}

function check_parity(frm) {
	// Reads both sides and writes to neither. This is the number that says whether
	// the data actually landed — an empty leave balance looks the same whether the
	// sync never ran or ran and wrote nothing.
	console.info("[HRMSERPInstance] checking parity against", frm.doc.name);
	frappe.call({
		// The PERSISTING entry point: same comparison as the pure GET
		// parity_check, plus an HRMS Parity Check row — the cutover criterion
		// counts consecutive clean runs, so the verdict must outlive this dialog.
		method: "hrms.sync.parity.run_parity_check",
		args: { instance_name: frm.doc.name },
		freeze: true,
		freeze_message: __("Counting rows on both sides…"),
		callback: (r) => {
			report_parity(r.message || {});
			show_sync_headline(frm); // streak may have just changed
		},
		error: (e) => console.warn("[HRMSERPInstance] parity check failed:", e),
	});
}

function report_parity(report) {
	const esc = frappe.utils.escape_html;
	const lines = report.lines || [];
	const clean = report.in_parity;

	if (clean) console.info("[HRMSERPInstance] in full parity");
	else console.warn("[HRMSERPInstance] parity variance:", report.mismatched, report.errored);

	const rows = lines
		.map((line) => {
			const state = line.error
				? `<span style="color:var(--red-500)">${esc(line.error)}</span>`
				: line.delta === 0
					? `<span style="color:var(--green-600)">${__("in parity")}</span>`
					: `<span style="color:var(--orange-500)">${__("{0} missing here", [
							line.delta,
						])}</span>`;
			return `<tr>
				<td>${esc(line.doctype)}</td>
				<td style="text-align:right">${line.remote ?? "—"}</td>
				<td style="text-align:right">${line.local ?? "—"}</td>
				<td>${state}</td>
			</tr>`;
		})
		.join("");

	frappe.msgprint({
		title: clean ? __("In parity") : __("Not in parity"),
		indicator: clean ? "green" : "orange",
		message:
			`<table class="table table-bordered" style="margin:0">
				<thead><tr>
					<th>${__("Doctype")}</th>
					<th style="text-align:right">${__("On source")}</th>
					<th style="text-align:right">${__("Here")}</th>
					<th>${__("State")}</th>
				</tr></thead>
				<tbody>${rows}</tbody>
			</table>` +
			((report.not_on_source || []).length
				? `<p class="text-muted">${__("Not on this source, so not compared: {0}", [
						report.not_on_source.map(esc).join(", "),
					])}</p>`
				: "") +
			(clean
				? `<p>${__("Every mirrored doctype matches the source.")}</p>`
				: `<p>${__(
						"A positive difference means rows have not landed here yet. Run a full sync; anything still missing afterwards is named in the run's error log.",
					)}</p>`),
	});
}

function sync_now(frm) {
	frappe.confirm(
		__("Pull HR data from {0} into this hub?", [frappe.utils.escape_html(frm.doc.name)]) +
			`<p class="text-muted">${__(
				"Reads only. Local rows are never deleted, and rows whose company or employee is missing here are skipped and reported.",
			)}</p>`,
		() => start_sync(frm, 0),
	);
}

function start_sync(frm, force) {
	console.info("[HRMSERPInstance] queueing full sync from", frm.doc.name, "force:", force);
	frappe.call({
		// Queued, never inline. A full pull takes minutes and the gateway kills the
		// request at ~2 — which does not merely fail, it kills the worker mid-write
		// and leaves the run record stuck at Running.
		method: "hrms.sync.runner.enqueue_sync",
		// Full pull, not incremental: the operator reaches for this button after
		// fixing something, and a watermark would hide the repair.
		args: { instance_name: frm.doc.name, incremental: 0, force: force || 0 },
		freeze: true,
		freeze_message: __("Queueing…"),
		callback: (r) => report_queued(r.message || {}, frm),
		error: (e) => console.warn("[HRMSERPInstance] could not queue the sync:", e),
	});
}

function report_queued(res, frm) {
	// No polling: the run record is written before the first remote read, and the
	// Desk list view refreshes itself as the run finishes.
	const runs = `<a href="/app/hrms-sync-run?source_instance=${encodeURIComponent(
		res.instance || "",
	)}">${__("Open HRMS Sync Run")}</a>`;

	if (res.queued) {
		console.info("[HRMSERPInstance] sync queued for", res.instance);
		frappe.msgprint({
			title: __("Sync queued"),
			indicator: "blue",
			message: `<p>${__(
				"Running in the background — this takes minutes, and you can leave this page.",
			)}</p><p>${runs}</p>`,
		});
		return;
	}

	console.warn("[HRMSERPInstance] not queued:", res.reason, res);

	// Every refusal names something the operator can act on. A bare "already in
	// progress" is what hid a job queued on a worker-less queue for an afternoon.
	if (res.reason === "no_worker") {
		frappe.msgprint({
			title: __("No background worker"),
			indicator: "red",
			message:
				`<p>${__(
					"Nothing is consuming the {0} queue on this site, so a queued sync would never start. No job was created.",
					[`<b>${frappe.utils.escape_html(res.queue || "long")}</b>`],
				)}</p>` +
				`<p>${__(
					"Ask whoever runs this site to start a background worker for that queue.",
				)}</p>`,
		});
		return;
	}

	if (res.reason === "already_queued") {
		frappe.msgprint({
			title: __("Already queued"),
			indicator: "orange",
			message:
				`<p>${__("A sync from {0} is queued and waiting for a worker.", [
					frappe.utils.escape_html(res.instance || ""),
				])}</p>` +
				`<p>${__(
					"If it has been waiting a long time it is stuck, and you can clear it and start again.",
				)}</p>`,
			primary_action: {
				label: __("Clear it and start again"),
				action() {
					frappe.hide_msgprint();
					start_sync(frm, 1);
				},
			},
		});
		return;
	}

	frappe.msgprint({
		title: __("Already running"),
		indicator: "orange",
		message:
			`<p>${__("A sync from {0} is in progress.", [
				frappe.utils.escape_html(res.instance || ""),
			])}</p>` +
			(res.run
				? `<p><a href="/app/hrms-sync-run/${encodeURIComponent(res.run)}">${__(
						"Open the run in progress",
					)}</a></p>`
				: `<p>${runs}</p>`),
	});
}

function pull_companies(frm) {
	// Preview first: HR sees exactly what would be created before anything is.
	frappe.call({
		method: "hrms.sync.company_shells.preview_company_shells",
		args: { instance_name: frm.doc.name },
		freeze: true,
		freeze_message: __("Reading companies from {0}…", [
			frappe.utils.escape_html(frm.doc.name),
		]),
		callback: (r) => {
			const plan = r.message || {};
			const missing = (plan.to_create || []).map((p) => p.company_name);

			const unregistered = plan.unregistered || [];

			if (!missing.length) {
				// "Nothing to create" was green and final, which is how a company
				// that exists here but is not served by this instance stayed
				// invisible — and its employees out of every sync.
				if (unregistered.length) {
					frappe.confirm(
						(plan.unmapped
							? __(
									"List {0} company(ies) under Companies Served? This NARROWS what this instance syncs.",
									[unregistered.length],
								)
							: __("Add {0} company(ies) to Companies Served?", [
									unregistered.length,
								])) + summary_html(plan, []),
						() => register_existing(frm, unregistered),
					);
					return;
				}
				frappe.msgprint({
					title: __("Nothing to create"),
					indicator: "green",
					message: summary_html(plan, []),
				});
				return;
			}

			frappe.confirm(
				__("Create {0} missing company record(s) as HR shells?", [missing.length]) +
					summary_html(plan, missing),
				() => create_shells(frm),
			);
		},
	});
}

function create_shells(frm) {
	frappe.call({
		method: "hrms.sync.company_shells.create_company_shells",
		args: { instance_name: frm.doc.name },
		freeze: true,
		freeze_message: __("Creating company shells…"),
		callback: (r) => {
			const result = r.message || {};
			frappe.msgprint({
				title: __("Company shells"),
				indicator: (result.failed || []).length ? "orange" : "green",
				message: result_html(result),
			});
			frm.reload_doc();
		},
	});
}

function summary_html(plan, missing) {
	const esc = frappe.utils.escape_html;
	const parts = [];

	if (missing.length)
		parts.push(`<p>${__("Missing locally")}: <b>${missing.map(esc).join(", ")}</b></p>`);
	if ((plan.existing || []).length)
		parts.push(`<p>${__("Already exist")}: ${plan.existing.map(esc).join(", ")}</p>`);
	if ((plan.unregistered || []).length)
		parts.push(
			`<p><b>${__("On the source and present here, but NOT listed under Companies Served")}</b>: ${plan.unregistered
				.map(esc)
				.join(", ")}<br><span class="text-muted">${
				plan.unmapped
					? __(
							"Companies Served is empty, so this instance currently syncs EVERY company. Listing them narrows it to these — and sets the company fence, the staff ERP redirect and the parity scope.",
						)
					: __(
							"Their employees are excluded from every sync until they are listed under Companies Served.",
						)
			}</span></p>`,
		);
	for (const row of plan.incomplete || [])
		parts.push(
			`<p>${__("Cannot create {0} — source is missing {1}", [
				`<b>${esc(row.name)}</b>`,
				esc(row.missing.join(", ")),
			])}</p>`,
		);

	return parts.length
		? `<hr>${parts.join("")}`
		: `<p>${__("All source companies exist here.")}</p>`;
}

function result_html(result) {
	const esc = frappe.utils.escape_html;
	const parts = [];

	if ((result.created || []).length)
		parts.push(`<p>${__("Created")}: <b>${result.created.map(esc).join(", ")}</b></p>`);
	if ((result.registered || []).length)
		parts.push(
			`<p>${__("Added to this instance's company list")}: ${result.registered
				.map(esc)
				.join(", ")}</p>`,
		);
	for (const row of result.failed || [])
		parts.push(`<p>${__("Failed")}: <b>${esc(row.company)}</b> — ${esc(row.error)}</p>`);
	for (const row of result.registration_errors || [])
		parts.push(
			`<p>${__("Created but not added to the company list")}: <b>${esc(
				row.company,
			)}</b> — ${esc(row.error)}</p>`,
		);
	if (!parts.length) parts.push(`<p>${__("Nothing was created.")}</p>`);

	return parts.join("");
}

//: Remove everything this hub mirrored from one instance.
//
// Deleting mirrored rows from the list view does not work and the error does not
// say why: the write-block ALLOWS it under System Manager break-glass, and then
// Frappe's link validation refuses because Employee is the last thing the sync
// writes and the first thing every other mirrored row points at. What the
// operator sees is "Bulk Operation Failed: 107 documents".
//
// This deletes in reverse sync order instead, and shows the dry run first —
// nothing is destroyed until the instance name is typed back.
function release_stamp(frm) {
	// Dry-run first (no confirm) — count what carries this instance's stamp, then
	// make the operator type the name, exactly like Purge. Unlike Purge this DELETES
	// NOTHING: it clears the provenance so a full sync from the real source can
	// reclaim rows a cloned instance wrongly stamped first.
	console.info("[HRMSERPInstance] release stamp dry-run for", frm.doc.name);
	frappe.call({
		method: "hrms.sync.purge.release_instance_stamp",
		args: { instance_name: frm.doc.name },
		freeze: true,
		freeze_message: __("Counting stamped rows…"),
		callback: ({ message }) => {
			if (!message || !message.total) {
				frappe.msgprint({
					title: __("Nothing to release"),
					indicator: "green",
					message: __("No rows on this hub carry {0}'s provenance stamp.", [frm.doc.name]),
				});
				return;
			}
			const lines = Object.entries(message.counts)
				.map(([doctype, n]) => `<li>${frappe.utils.escape_html(doctype)}: <b>${n}</b></li>`)
				.join("");
			const d = new frappe.ui.Dialog({
				title: __("Release provenance stamp"),
				fields: [
					{
						fieldtype: "HTML",
						options: `<p>${__("This clears the provenance stamp on <b>{0}</b> rows mirrored from <b>{1}</b>. It <b>deletes nothing</b> — the rows stay, they just stop being attributed to this instance.", [message.total, frappe.utils.escape_html(frm.doc.name)])}</p>
							<ul>${lines}</ul>
							<p>${__("Do this for a cloned/dev instance, then run a full sync from the REAL source: it reclaims every row that source genuinely holds. Whatever is still unstamped afterwards is clone-only data.")}</p>`,
					},
					{
						fieldtype: "Data",
						fieldname: "confirm",
						reqd: 1,
						label: __("Type the instance name to confirm"),
						description: frm.doc.name,
					},
				],
				primary_action_label: __("Release Stamp"),
				primary_action: ({ confirm }) => {
					d.hide();
					frappe.call({
						method: "hrms.sync.purge.release_instance_stamp",
						args: { instance_name: frm.doc.name, confirm },
						freeze: true,
						freeze_message: __("Releasing…"),
						callback: (r) => {
							const res = r.message || {};
							frappe.msgprint({
								title: __("Stamp released"),
								indicator: "green",
								message: __(
									"Released {0} row(s) — now hub-owned. Run a full sync from the real source to reclaim what it holds.",
									[res.total],
								),
							});
							frm.reload_doc();
						},
					});
				},
			});
			d.show();
		},
	});
}

function purge_mirror(frm) {
	frappe.call({
		method: "hrms.sync.purge.purge_instance",
		args: { instance_name: frm.doc.name },
		freeze: true,
		freeze_message: __("Counting mirrored rows…"),
		callback: ({ message }) => {
			if (!message || !message.total) {
				frappe.msgprint({
					title: __("Nothing to purge"),
					indicator: "green",
					message: __("No rows on this hub carry {0}'s provenance stamp.", [
						frm.doc.name,
					]),
				});
				return;
			}
			const lines = Object.entries(message.counts)
				.map(
					([doctype, n]) => `<li>${frappe.utils.escape_html(doctype)}: <b>${n}</b></li>`,
				)
				.join("");
			const d = new frappe.ui.Dialog({
				title: __("Purge mirrored data"),
				fields: [
					{
						fieldtype: "HTML",
						options: `<p>${__("This deletes <b>{0}</b> rows mirrored from <b>{1}</b>, in reverse sync order.", [message.total, frappe.utils.escape_html(frm.doc.name)])}</p>
							<ul>${lines}</ul>
							<p>${__("Rows a local document still links to are reported, never force-deleted. Masters and hub-owned rows are not touched.")}</p>`,
					},
					{
						fieldtype: "Data",
						fieldname: "confirm",
						reqd: 1,
						label: __("Type the instance name to confirm"),
						description: frm.doc.name,
					},
				],
				primary_action_label: __("Purge"),
				primary_action: ({ confirm }) => {
					d.hide();
					frappe.call({
						method: "hrms.sync.purge.purge_instance",
						args: { instance_name: frm.doc.name, confirm },
						freeze: true,
						freeze_message: __("Purging…"),
						callback: (r) => {
							const res = r.message || {};
							const blocked = (res.blocked || []).length;
							frappe.msgprint({
								title: __("Purge complete"),
								indicator: blocked ? "orange" : "green",
								message: blocked
									? __(
											"Deleted {0} of {1}. {2} row(s) were left because a local document links to them — see the Error Log for which.",
											[res.deleted, res.total, blocked],
										)
									: __("Deleted {0} row(s).", [res.deleted]),
							});
							frm.reload_doc();
						},
					});
				},
			});
			d.show();
		},
	});
}

//: List companies that already exist here against this instance.
//
// create_company_shells registers only what it CREATED, deliberately — claiming
// a company for an instance is a human decision. This is that decision made
// explicitly. The candidates come from the source's own list, so an arbitrary
// company cannot be claimed here.
function register_existing(frm, companies) {
	frappe.call({
		method: "hrms.sync.company_shells.register_existing_companies",
		args: { instance_name: frm.doc.name, companies: JSON.stringify(companies) },
		freeze: true,
		freeze_message: __("Registering…"),
		callback: (r) => {
			const res = r.message || {};
			const errors = res.errors || [];
			frappe.msgprint({
				title: __("Companies Served updated"),
				indicator: errors.length ? "orange" : "green",
				message: errors.length
					? __(
							"Registered {0}. {1} could not be added — another instance may already claim them.",
							[(res.registered || []).join(", "), errors.length],
						)
					: __("Registered: {0}", [(res.registered || []).join(", ")]),
			});
			frm.reload_doc();
		},
	});
}

//: State the scope this table is CURRENTLY in effect for.
//
// An empty child table under a heading that read "Employees of these companies
// are sent to this instance" says "none" to every reader, and it means "all".
// An operator spent an afternoon on that: 312 employees had synced correctly
// and the form showed a blank table, so it looked like nothing had been fetched.
//
// Empty is the PERMISSIVE setting. The form now says so where the emptiness is,
// rather than leaving the reader to infer it from `runner.instance_companies`.
function show_company_scope(frm) {
	const field = frm.get_field("companies");
	if (!field) return;

	const rows = (frm.doc.companies || []).length;
	field.df.description = rows
		? __(
				"Serving {0} company(ies). Employees of any OTHER company on the source are NOT synced, and HR (Instance) users are fenced to these.",
				[rows],
			)
		: __(
				"EMPTY = every company. This instance currently syncs employees from ALL companies on the source — empty is the permissive setting, not a missing one. Add rows only to narrow it.",
			);
	field.refresh();
}

function check_sources() {
	// Site-wide, not per-instance, deliberately: the failure it looks for is two
	// instances claiming the SAME rows, which is invisible from either one alone.
	console.info("[HRMSERPInstance] reading the source census");
	frappe.call({
		method: "hrms.sync.diagnose.source_census",
		freeze: true,
		freeze_message: __("Counting rows by source…"),
		callback: (r) => report_sources(r.message || {}),
		error: (e) => console.warn("[HRMSERPInstance] source census failed:", e),
	});
}

function report_sources(census) {
	const esc = frappe.utils.escape_html;
	const rows = census.rows || [];
	const clean = census.verdict === "one-source";

	if (!clean) console.warn("[HRMSERPInstance] more than one source in play:", census.claiming);

	const table = rows
		.map((r) => {
			const by = Object.entries(r.by_source || {})
				.map(([k, v]) => `${esc(k)} = ${v}`)
				.join("<br>");
			return `<tr>
				<td>${esc(r.doctype)}</td>
				<td style="text-align:right">${r.total}</td>
				<td style="text-align:right">${r.hub_owned}</td>
				<td>${by || "&mdash;"}</td>
			</tr>`;
		})
		.join("");

	// Named "last touched by", never "came from". On a hub that ran two
	// colliding instances those are different things, and the whole reason this
	// dialog exists is that the column header used to imply the stronger one.
	const head = `<table class="table table-bordered" style="margin-bottom:12px">
		<thead><tr>
			<th>${__("Doctype")}</th>
			<th style="text-align:right">${__("Rows")}</th>
			<th style="text-align:right">${__("Written here")}</th>
			<th>${__("Last touched by")}</th>
		</tr></thead><tbody>${table}</tbody></table>`;

	const orphans = (census.orphan_stamps || []).length
		? `<p><b>${__("Stamped with an instance that is not registered")}:</b><br>
			${census.orphan_stamps.map(esc).join(", ")}<br>
			<span class="text-muted">${__("These rows cannot be re-synced and Purge cannot reach them.")}</span></p>`
		: "";

	const unlocked = (census.unlocked || []).length
		? `<p style="color:var(--red-600)"><b>${__("Writes are UNLOCKED on")} ${census.unlocked.map(esc).join(", ")}.</b><br>
			${__("Local edits to those rows will be overwritten by the next pull.")}</p>`
		: "";

	const verdict = clean
		? `<p style="color:var(--green-600)"><b>${__("One source.")}</b>
			${__("The provenance column means what it says.")}</p>`
		: `<p style="color:var(--red-600)"><b>${__("More than one source is in play")}:
			${(census.claiming || []).map(esc).join(", ") || __("none synced yet")}.</b></p>
			<p>${__("If one of these is a COPY of another (a dev ERP cloned from live), the column above is unreliable — it records which instance synced LAST, not where a row originated.")}</p>
			<p><b>${__("Do not Purge.")}</b> ${__("Purge deletes by that column, so it would take live rows. Safe order:")}</p>
			<ol>
				<li>${__("Disable every instance except the real live one")}</li>
				<li>${__("Release the clone's stamp — this deletes nothing")}</li>
				<li>${__("Run a full sync from live; it reclaims and rewrites what live holds")}</li>
				<li>${__("Re-open this dialog. What is still unregistered is clone-only data")}</li>
			</ol>`;

	frappe.msgprint({
		title: __("Where did this data come from?"),
		indicator: clean ? "green" : "red",
		message: head + orphans + unlocked + verdict,
		wide: true,
	});
}
