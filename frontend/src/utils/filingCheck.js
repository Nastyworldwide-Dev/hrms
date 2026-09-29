// When to ask the server's "would this be refused?" check for a leave being
// filed, and which answer belongs to what is on screen (owner, 29 Sep 2026:
// guide everyone, before Send; alpha.21). Pure.

export function readyToCheck(doc = {}) {
	const { leave_type, from_date, to_date } = doc
	return Boolean(leave_type && from_date && to_date && from_date <= to_date)
}

//: The question an answer answers: the fields that change the server's verdict.
export function filingKey(doc = {}) {
	const { leave_type, from_date, to_date, half_day, half_day_date, half_day_session } = doc
	return JSON.stringify([leave_type, from_date, to_date, half_day ? 1 : 0, half_day_date || "", half_day_session || ""])
}
