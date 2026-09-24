// The primary button on a NEW request: "Send to {first name}" (owner ruling
// Q1, 24 Sep 2026), not "Save". A request is sent to a person; the button
// says to whom (Apple HIG Writing: buttons are verbs naming the result).
import { REQUEST_KIND } from "./requestKind.js"

//: The field naming who a request goes to, per doctype. Types routed by the
//: employee's chain (overtime, fix a day) have no picker: plain "Send".
const APPROVER_FIELD = {
	"Leave Application": "leave_approver",
	"Expense Claim": "expense_approver",
	"Shift Request": "approver",
}

export function sendLabel({ doctype, isNew, fields, model }) {
	if (!isNew) return "Save"
	if (doctype === "Employee Issue") return "Send to HR"
	if (!REQUEST_KIND[doctype]) return "Save"
	const field = APPROVER_FIELD[doctype]
	const login = field && model?.[field]
	const option = login && (fields || []).find((f) => f.fieldname === field)?.documentList?.find((o) => o.value === login)
	const first = option?.label?.split(/\s+/)[0]
	return first ? `Send to ${first}` : "Send"
}
