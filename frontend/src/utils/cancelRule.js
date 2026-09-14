// Owner rule: an approved request is never cancelled. The server refuses it; this
// keeps the PWA from offering a Cancel that can only fail. Rejected stays cancellable.

// No decision field on these — submission IS the approval.
const APPROVED_ON_SUBMIT = ["Compensatory Leave Request", "Employee Advance", "Travel Request"]

export function canOfferCancel(doc, doctype = doc?.doctype) {
	if (Number(doc?.docstatus) !== 1) return false
	// No decision field: only HR Manager / System Manager may cancel (to correct a
	// mistake), and only they hold `cancel` on these, so the permission check decides.
	if (APPROVED_ON_SUBMIT.includes(doctype)) return true
	const decision = doctype === "Expense Claim" ? doc.approval_status : doc.status
	return decision !== "Approved"
}
