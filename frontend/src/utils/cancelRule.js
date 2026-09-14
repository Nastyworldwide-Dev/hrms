// Owner rule: an approved request is never cancelled. The server refuses it; this
// keeps the PWA from offering a Cancel that can only fail. Rejected stays cancellable.

// No decision field on these — submission IS the approval.
const APPROVED_ON_SUBMIT = ["Compensatory Leave Request", "Employee Advance", "Travel Request"]

// Owner ruling, 14 Sep 2026: "leave, attendance yes ... overtime no ... only HR can
// edit overtime." Only HR User, HR Manager and System Manager hold `cancel` on OT
// Request (hrms/hr/doctype/ot_request/ot_request.json) — Employee does not — so an
// approved OT Request defers entirely to the cancel permission, unlike every other
// decision doctype above, which stays hidden from everyone once approved.
const HR_ONLY_CANCELLABLE_WHEN_APPROVED = ["OT Request"]

export function canOfferCancel(doc, doctype = doc?.doctype) {
	if (Number(doc?.docstatus) !== 1) return false
	// No decision field: only HR Manager / System Manager may cancel (to correct a
	// mistake), and only they hold `cancel` on these, so the permission check decides.
	if (APPROVED_ON_SUBMIT.includes(doctype)) return true
	if (HR_ONLY_CANCELLABLE_WHEN_APPROVED.includes(doctype)) return true
	const decision = doctype === "Expense Claim" ? doc.approval_status : doc.status
	return decision !== "Approved"
}
