// Hours are stored to 9 decimals for pay; HR reads them to 2 (1.50).
// Blank stays blank: a missing value is not "0.00 hours".
const two_decimals = (value) => (value == null || value === "" ? "" : format_number(value, null, 2));

frappe.listview_settings["OT Request"] = {
	formatters: {
		claimed_hours: two_decimals,
	},
};

// The REPORT view never reads listview_settings.formatters: it formats each
// cell through the docfield, and honours a formatter set on the docfield
// itself (owner ruling 25 Sep 2026: "1.50" in HR's OT Request report). Frappe
// builds docfield_map from the meta before it runs this script, so the field is
// there to carry it. Display only; the stored 9 decimals are untouched.
const claimed_hours_df = frappe.meta.docfield_map?.["OT Request"]?.claimed_hours;
if (claimed_hours_df) {
	// Right-aligned like every number column (Frappe's own _right wrapper);
	// inline contexts get the bare number.
	claimed_hours_df.formatter = (value, df, options) =>
		frappe.form.formatters._right(two_decimals(value), options);
	console.info("[OT Request] claimed hours display to 2 decimals");
}
