// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("HRMS ERP Instance", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.enabled) return;

		// Ordered as the operator must run them: companies first, because an
		// Employee whose company is absent here is skipped, not written.
		frm.add_custom_button(__("Pull Companies from Source"), () => pull_companies(frm));
		frm.add_custom_button(__("Sync Employee Data"), () => sync_now(frm));
	},
});

function sync_now(frm) {
	frappe.confirm(
		__("Pull HR data from {0} into this hub?", [frappe.utils.escape_html(frm.doc.name)]) +
			`<p class="text-muted">${__(
				"Reads only. Local rows are never deleted, and rows whose company or employee is missing here are skipped and reported.",
			)}</p>`,
		() => {
			console.info("[HRMSERPInstance] queueing full sync from", frm.doc.name);
			frappe.call({
				// Queued, never inline. A full pull takes minutes and the gateway
				// kills the request at ~2 — which does not merely fail, it kills the
				// worker mid-write and leaves the run record stuck at Running.
				method: "hrms.sync.runner.enqueue_sync",
				// Full pull, not incremental: the operator reaches for this button
				// after fixing something, and a watermark would hide the repair.
				args: { instance_name: frm.doc.name, incremental: 0 },
				freeze: true,
				freeze_message: __("Queueing…"),
				callback: (r) => report_queued(r.message || {}),
				error: (e) => console.warn("[HRMSERPInstance] could not queue the sync:", e),
			});
		},
	);
}

function report_queued(res) {
	// No polling: the run record is written before the first remote read, and the
	// Desk list view refreshes itself as the run finishes.
	const runs = `<a href="/app/hrms-sync-run?source_instance=${encodeURIComponent(res.instance || "")}">${__(
		"Open HRMS Sync Run to watch it",
	)}</a>`;

	if (!res.queued) {
		console.warn("[HRMSERPInstance] not queued:", res.reason, res);
		frappe.msgprint({
			title: __("Already running"),
			indicator: "orange",
			message: `<p>${__("A sync from {0} is already in progress.", [
				frappe.utils.escape_html(res.instance || ""),
			])}</p><p>${runs}</p>`,
		});
		return;
	}

	console.info("[HRMSERPInstance] sync queued for", res.instance);
	frappe.msgprint({
		title: __("Sync queued"),
		indicator: "blue",
		message:
			`<p>${__(
				"Running in the background — this takes minutes, and you can leave this page.",
			)}</p><p>${runs}</p>`,
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
