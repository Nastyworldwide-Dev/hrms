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
			console.info("[HRMSERPInstance] starting full sync from", frm.doc.name);
			frappe.call({
				method: "hrms.sync.runner.run_sync",
				// Full pull, not incremental: the operator reaches for this button
				// after fixing something, and a watermark would hide the repair.
				args: { instance_name: frm.doc.name, incremental: 0 },
				freeze: true,
				// ponytail: synchronous. SYNC-00002 pulled 5,821 rows in 25s, well
				// inside the gateway timeout. Move to frappe.enqueue with a realtime
				// notification if a run ever approaches it.
				freeze_message: __("Syncing from {0}…", [frappe.utils.escape_html(frm.doc.name)]),
				callback: (r) => report_run(r.message || {}),
				error: (e) => console.warn("[HRMSERPInstance] sync call failed:", e),
			});
		},
	);
}

function report_run(res) {
	// "Completed" requires nothing left unwritten, so anything else has to name
	// what to fix — a bare status tells the operator to guess.
	const clean = res.status === "Completed";
	if (clean) console.info("[HRMSERPInstance] sync completed:", res.run, res.written, "row(s) written");
	else console.warn("[HRMSERPInstance] sync ended", res.status, "run:", res.run, res);

	frappe.msgprint({
		title: __("Sync {0}", [res.status || __("finished")]),
		indicator: clean ? "green" : "orange",
		message:
			`<p>${__("Pulled {0}, written {1}, skipped {2}, orphaned {3}, errored {4}.", [
				res.pulled ?? 0,
				res.written ?? 0,
				res.skipped ?? 0,
				res.orphaned ?? 0,
				res.errored ?? 0,
			])}</p>` +
			(clean
				? ""
				: `<p>${__("Rows were left unwritten, so the watermark is held and they are re-pulled next run.")}</p>`) +
			(res.run
				? `<p><a href="/app/hrms-sync-run/${encodeURIComponent(res.run)}">${__(
						"Open the run record for the reason",
					)}</a></p>`
				: ""),
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
