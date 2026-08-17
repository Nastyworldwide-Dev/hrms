// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("HRMS ERP Instance", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.enabled) return;

		// Ordered as the operator must run them: companies first, because an
		// Employee whose company is absent here is skipped, not written.
		frm.add_custom_button(__("Pull Companies from Source"), () => pull_companies(frm));
		frm.add_custom_button(__("Sync Employee Data"), () => sync_now(frm));
		frm.add_custom_button(__("Check Data Parity"), () => check_parity(frm));
	},
});

function check_parity(frm) {
	// Reads both sides and writes to neither. This is the number that says whether
	// the data actually landed — an empty leave balance looks the same whether the
	// sync never ran or ran and wrote nothing.
	console.info("[HRMSERPInstance] checking parity against", frm.doc.name);
	frappe.call({
		method: "hrms.sync.parity.parity_check",
		args: { instance_name: frm.doc.name },
		freeze: true,
		freeze_message: __("Counting rows on both sides…"),
		callback: (r) => report_parity(r.message || {}),
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
					: `<span style="color:var(--orange-500)">${__("{0} missing here", [line.delta])}</span>`;
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
	const runs = `<a href="/app/hrms-sync-run?source_instance=${encodeURIComponent(res.instance || "")}">${__(
		"Open HRMS Sync Run",
	)}</a>`;

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
				`<p>${__("Ask whoever runs this site to start a background worker for that queue.")}</p>`,
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
				`<p>${__("If it has been waiting a long time it is stuck, and you can clear it and start again.")}</p>`,
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

			if (!missing.length) {
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
	for (const row of plan.incomplete || [])
		parts.push(
			`<p>${__("Cannot create {0} — source is missing {1}", [
				`<b>${esc(row.name)}</b>`,
				esc(row.missing.join(", ")),
			])}</p>`,
		);

	return parts.length ? `<hr>${parts.join("")}` : `<p>${__("All source companies exist here.")}</p>`;
}

function result_html(result) {
	const esc = frappe.utils.escape_html;
	const parts = [];

	if ((result.created || []).length)
		parts.push(`<p>${__("Created")}: <b>${result.created.map(esc).join(", ")}</b></p>`);
	if ((result.registered || []).length)
		parts.push(`<p>${__("Added to this instance's company list")}: ${result.registered.map(esc).join(", ")}</p>`);
	for (const row of result.failed || [])
		parts.push(`<p>${__("Failed")}: <b>${esc(row.company)}</b> — ${esc(row.error)}</p>`);
	for (const row of result.registration_errors || [])
		parts.push(
			`<p>${__("Created but not added to the company list")}: <b>${esc(row.company)}</b> — ${esc(row.error)}</p>`,
		);
	if (!parts.length) parts.push(`<p>${__("Nothing was created.")}</p>`);

	return parts.join("");
}
