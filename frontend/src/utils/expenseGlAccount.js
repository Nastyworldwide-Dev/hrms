// The GL account an expense line posts to, shown as its own read-only row right
// under Type (owner, 29 Oct 2026). It used to arrive as "GL: Travel Expenses"
// typed into the Description, where staff could edit it. The account actually
// posted is still set by the server on save (ExpenseClaim.set_expense_account);
// this row only shows it.

//: The row's key on the line. Not a field of Expense Claim Detail, so it is
//: stripped before the line is saved (withoutGlAccount).
export const GL_FIELD = "gl_account_shown"

/**
 * `fields` with a read-only "GL account" row after `expense_type`, showing
 * `account`. No account (no type picked, or none set for this company): no row.
 */
export function withGlAccountField(fields, account, __ = (text) => text) {
	if (!account) return fields
	const row = {
		fieldname: GL_FIELD,
		fieldtype: "Data",
		label: __("GL account"),
		read_only: 1,
		default: account,
	}
	const at = fields.findIndex((field) => field.fieldname === "expense_type")
	if (at === -1) return [...fields, row]
	return [...fields.slice(0, at + 1), row, ...fields.slice(at + 1)]
}

/** The line as it is saved: the shown-only GL row taken off. */
export function withoutGlAccount(item) {
	const line = { ...item }
	delete line[GL_FIELD]
	return line
}
