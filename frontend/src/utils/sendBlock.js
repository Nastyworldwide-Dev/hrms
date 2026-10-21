// Why Send is dimmed, in words, or "" when it is not (UX review 21 Oct 2026,
// F1/F4). Pages hand the result to FormView's saveError, which both dims Send
// and shows this line by it, so a dimmed Send always says why (#4855 class).

/** A required approver HR has not set: the person cannot fix it here. */
export function noApproverReason(details, field, __) {
	if (!details?.is_mandatory || details[field]) return ""
	return __("No one is set to approve this for you yet. Ask HR to set your approver.")
}

export function expenseSendBlock(claim, approval, __) {
	return (
		noApproverReason(approval, "expense_approver", __) ||
		(claim?.expenses?.length ? "" : __("Add at least one expense."))
	)
}
