// Owner ruling, 14 Sep 2026 (reverses 13 Sep): HR and the request's approver —
// named in the approver field or the employee's reports_to manager — may cancel an
// approved request of any type; the request's own employee, and anyone else, may
// not. hrms/utils/approved_request_guard.py holds the rule on the server; the PWA
// asks it through hrms.api.approval.can_cancel_approved (composables/approvedCancel.js)
// rather than keeping a second copy here.
//
// Returns
//   "own"      submitted, not approved — offer Cancel only with the cancel DocPerm
//   "approved" approved, viewer is not the employee — offer Cancel only when the
//              server says so; hrms.api.approval.finalize elevates the routed cancel
//   false      no Cancel

// No decision field on these — submission IS the approval. Compensatory Leave
// Request left this list on 15 Sep 2026: it decides in `status` and can be rejected.
const APPROVED_ON_SUBMIT = ["Employee Advance", "Travel Request"]

export function canOfferCancel(doc, doctype = doc?.doctype, viewer = {}) {
	if (Number(doc?.docstatus) !== 1) return false
	const decision = doctype === "Expense Claim" ? doc.approval_status : doc.status
	if (!APPROVED_ON_SUBMIT.includes(doctype) && decision !== "Approved") return "own"
	const own = Boolean(viewer?.employee && doc.employee === viewer.employee)
	console.info("[cancelRule] approved", doctype, doc?.name, "own request:", own)
	return own ? false : "approved"
}
