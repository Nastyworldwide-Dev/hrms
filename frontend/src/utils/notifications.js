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
// on the Remote Approvals screen. A pending request lands on its queue; a
// decided one lands on the History tab where the decision stays reviewable.
export function notificationRoute(item, remoteStatus, hasRoute) {
	const doctype = item?.reference_document_type
	if (!doctype) return null

	if (doctype === "Remote Checkin Request") {
		return {
			name: "RemoteApprovals",
			query: { tab: remoteStatus === "Pending" ? "Pending" : "History" },
		}
	}

	const name = `${doctype.replace(/\s+/g, "")}DetailView`
	if (!hasRoute(name)) return null
	return { name, params: { id: item.reference_document_name } }
}
