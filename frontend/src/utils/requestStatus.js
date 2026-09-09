// Chip state for a request whose decision lives in `status` (OT Request,
// Replacement Leave Claim). Both are submitted on rejection too — the decision
// is recorded in `status`, the submit seals it — so a chip that read docstatus
// alone showed a rejected claim as "Approved".
export function requestStatusChip(doc = {}) {
	const docstatus = Number(doc.docstatus ?? 0)
	if (docstatus === 2) return "Cancelled"
	if (doc.status === "Rejected") return "Rejected"
	if (docstatus === 1) return "Approved"
	return "Pending"
}
