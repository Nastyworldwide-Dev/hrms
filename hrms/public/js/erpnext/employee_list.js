// Employee list colours for HR's five statuses (10 Nov 2026). ERPNext's own
// list script only colours Active / Inactive / Suspended / Left, so Resigned,
// Terminated and Deceased would show uncoloured. Resigned takes Left's grey.
const EMPLOYEE_STATUS_COLOURS = {
	Active: "green",
	Resigned: "gray",
	Terminated: "red",
	Deceased: "darkgrey",
	Suspended: "orange",
};

frappe.listview_settings["Employee"] = {
	...(frappe.listview_settings["Employee"] || {}),
	add_fields: ["status", "branch", "department", "designation", "image"],
	filters: [["status", "=", "Active"]],
	get_indicator(doc) {
		return [
			__(doc.status, null, "Employee"),
			EMPLOYEE_STATUS_COLOURS[doc.status] || "gray",
			"status,=," + doc.status,
		];
	},
};

if (typeof module !== "undefined") module.exports = { EMPLOYEE_STATUS_COLOURS };
