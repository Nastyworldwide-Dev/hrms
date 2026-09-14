// Owner ruling, 14 Sep 2026 (reverses 13 Sep): HR and the request's approver may
// cancel an approved request of any type; the request's own employee, and anyone
// else, may not. hrms/utils/approved_request_guard.py holds the rule on the server;
// this only keeps the PWA from offering a Cancel that can only fail.
//
// Returns
//   "own"      submitted, not approved — offer Cancel only with the cancel DocPerm
//   "approver" approved, viewer is HR or the named approver and not the employee —
//              offer Cancel; hrms.api.approval.finalize elevates the routed cancel
//   false      no Cancel
//
// A reports_to-only manager has no approver field to match, so the PWA does not
// offer them Cancel. Paid Overtime Pay OT is refused by the server with a payroll
// message.

// No decision field on these — submission IS the approval.
const APPROVED_ON_SUBMIT = ["Compensatory Leave Request", "Employee Advance", "Travel Request"]
const HR_ROLES = ["HR User", "HR Manager", "System Manager"]
// Mirrors hrms.api.approval.APPROVER_FIELD.
const APPROVER_FIELD = {
	"Leave Application": "leave_approver",
	"Expense Claim": "expense_approver",
	"Shift Request": "approver",
}

export function canOfferCancel(doc, doctype = doc?.doctype, viewer = {}) {
	if (Number(doc?.docstatus) !== 1) return false
	const decision = doctype === "Expense Claim" ? doc.approval_status : doc.status
	if (!APPROVED_ON_SUBMIT.includes(doctype) && decision !== "Approved") return "own"
	const field = APPROVER_FIELD[doctype]
	const approver =
		!(viewer?.employee && doc.employee === viewer.employee) &&
		((viewer?.roles || []).some((role) => HR_ROLES.includes(role)) ||
			Boolean(field && viewer?.user && doc[field] === viewer.user))
	console.info("[cancelRule] approved", doctype, doc?.name, "approver cancel:", approver)
	return approver ? "approver" : false
}
