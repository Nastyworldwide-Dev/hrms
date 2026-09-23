// The leave balance an approver reads must be the one the approve is judged by
// (owner screenshot, 23 Sep 2026). A Leave Application's leave_balance is a
// snapshot from filing; hrms.api.approval.get_decision_actions returns
// leave_balance_now — the number validate_balance_leaves uses — to a decider.

const isNumber = (value) => typeof value === "number" && Number.isFinite(value)

/** The balance to show: the live one when the server sent it, else the stored field. */
export function shownLeaveBalance(doc, balanceNow) {
	return isNumber(balanceNow) ? balanceNow : doc?.leave_balance
}

/** One plain line when the live balance cannot cover the days asked for, else "". */
export function shortLeaveNotice(doc, balanceNow, t) {
	if (!doc || !isNumber(balanceNow) || !(balanceNow < Number(doc.total_leave_days))) return ""
	console.info("[approval] leave balance short for", doc.leave_type, balanceNow)
	return t("Not enough {0} left for these dates ({1} left).", [doc.leave_type, balanceNow])
}
