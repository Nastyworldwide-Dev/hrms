// HR reads overtime hours to 2 decimals in the OT Request REPORT, not only the
// list (owner ruling, 25 Sep 2026: "as u recommended" — 1.50, stored to 9).
//
// Why a list formatter was not enough: Frappe's Report view formats a cell
// with frappe.format(value, column.docfield, { always_show_decimals: true }),
// which never reads listview_settings.formatters. It does read a formatter set
// on the docfield itself (frappe.form.formatters._apply_custom_formatter), so
// that is where the 2-decimal display lives. The stored value is untouched:
// pay and the claim cap still see all 9 decimals.
// Run: node --test hrms/hr/doctype/ot_request/ot_request_list.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function load() {
	const docfield_map = { "OT Request": { claimed_hours: { fieldname: "claimed_hours", fieldtype: "Float" } } };
	const settings = {};
	const sandbox = {
		frappe: {
			listview_settings: settings,
			meta: { docfield_map },
			provide: () => {},
			// Frappe's _right: a report cell is wrapped, an inline value is bare.
			form: { formatters: { _right: (v, o) => (o && (o.inline || o.only_value) ? v : `<right>${v}</right>`) } },
		},
		console: { info: () => {} },
		// Frappe's format_number(value, format, decimals), to the precision asked.
		format_number: (value, _f, decimals) => Number(value).toFixed(decimals),
	};
	vm.runInNewContext(fs.readFileSync(path.join(__dirname, "ot_request_list.js"), "utf8"), sandbox);
	return { settings, df: docfield_map["OT Request"].claimed_hours }
}

test("the report cell shows claimed hours to 2 decimals", () => {
	const { df } = load();
	assert.strictEqual(typeof df.formatter, "function", "the docfield carries the formatter");
	const cell = (v) => df.formatter(v, df, { always_show_decimals: true });
	assert.strictEqual(cell(1.5), "<right>1.50</right>", "right-aligned like any number");
	assert.strictEqual(cell(1.333333333), "<right>1.33</right>");
	assert.strictEqual(cell(0.75), "<right>0.75</right>");
	assert.strictEqual(cell(2), "<right>2.00</right>");
	assert.strictEqual(df.formatter(1.5, df, { inline: 1 }), "1.50", "inline is the bare number");
});

test("an empty cell stays empty, never 0.00", () => {
	const { df } = load();
	assert.strictEqual(df.formatter(null, df, { inline: 1 }), "");
	assert.strictEqual(df.formatter("", df, { inline: 1 }), "");
});

test("the list keeps the same 2-decimal display", () => {
	const { settings } = load();
	assert.strictEqual(settings["OT Request"].formatters.claimed_hours(1.5), "1.50");
});
