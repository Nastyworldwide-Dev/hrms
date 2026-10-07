// The words a read-only form row shows (alpha.7 B1): a yes/no is a word, a
// date is written out, a number is the number a person would say. Hours are
// punch-derived Floats ("10.026111111" on a sent OT request, 28 Sep 2026):
// at most two decimals, trailing zeros dropped, as formatHours does.
// `formatDate` (and `formatDateTime`) are passed in so this stays free of dayjs and testable in node.

export function readValue(fieldtype, value, formatDate, formatDateTime = formatDate) {
	if (fieldtype === "Check") return value ? "Yes" : "No"
	if (fieldtype === "Float") return (Math.round((Number(value) || 0) * 100) / 100).toString()
	if (fieldtype === "Int") return String(value)
	if (fieldtype === "Datetime") return value ? formatDateTime(value) : ""
	return value ? formatDate(value) : ""
}
