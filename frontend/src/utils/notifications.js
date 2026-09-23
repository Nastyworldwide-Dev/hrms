// Where a notification tap lands. Pure — the router is passed in as `hasRoute`
// so the contract is testable without vue-router.
//
// The route name for generic notifications is DERIVED from a server-supplied
// doctype, so the pairing is a contract with nothing enforcing it. That already
// bit once: "Remote Checkin Request" derived to RemoteCheckinRequestDetailView,
// which is not a registered route, and the tap silently did nothing. Anything
// that does not resolve to a real route returns null so the card renders as
// plain content instead of a link that goes nowhere.
//
// Remote Checkin Requests never derive: notifications notify, deciding happens
// on the Approvals page, where every check-in outside the area waits with the
// rest (AUDIT-PLAN, Approvals row).
//
// Time off in lieu and replacement leave have no detail page at all; the
// approver reaches them on Approvals too (alpha.5 review, 23 Sep 2026).
const TO_APPROVALS = new Set([
	"Remote Checkin Request",
	"Compensatory Leave Request",
	"Replacement Leave Claim",
])

export function notificationRoute(item, remoteStatus, hasRoute) {
	const doctype = item?.reference_document_type
	if (!doctype) return null

	if (TO_APPROVALS.has(doctype)) {
		return { name: "Approvals" }
	}

	const name = `${doctype.replace(/\s+/g, "")}DetailView`
	if (!hasRoute(name)) return null
	return { name, params: { id: item.reference_document_name } }
}
