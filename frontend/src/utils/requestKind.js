// The person's word for each request type — the same words the Approvals
// list uses (hrms/api/approvals_list.py KIND), so a request is called one
// thing everywhere. A doctype name ("Leave Application") is a table, not
// something people say (basis W-PLAIN).
export const REQUEST_KIND = {
	"Leave Application": "Time off",
	"Expense Claim": "Expense",
	"Shift Request": "Shift change",
	"Attendance Request": "Fix a day",
	"OT Request": "Overtime",
	"Replacement Leave Claim": "Replacement leave",
	"Compensatory Leave Request": "Time off in lieu",
	"Remote Checkin Request": "Check-in outside the area",
}

/**
 * The word for one request: a Fix a day sent as a time slip is a "Time slip"
 * (owner, 14 Oct 2026; same rule as approvals_list._row).
 */
export function requestKind(doctype, doc) {
	if (doctype === "Attendance Request" && doc?.reason === "Time Slip") return "Time slip"
	return REQUEST_KIND[doctype] || doctype || ""
}
