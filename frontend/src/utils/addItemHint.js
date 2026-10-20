// Why "Add expense" is dimmed, in words, or "" when it is not (alpha.60).
// The ONE rule: ExpensesTable dims Add exactly when this says something, so a
// dimmed button always has its reason (the #4855 class: a disabled Send that
// said nothing took three commits to cover; review of b7bb33cc9).
import { plainLabel } from "./plainLabel.js"

/**
 * `fields` are the sheet's fields as shown; `item` the line being added.
 * `__` is the app's translate (passed in so this runs in node).
 */
export function addItemHint({ fields, item, needsReceipt, uploading, loadFailed }, __) {
	if (loadFailed) return __("This form could not be loaded. Try again.")
	const empty = (fields || []).find((field) => field.reqd && !item[field.fieldname])
	// the row's own word ("Type", not "Expense Claim Type"), as FormField shows it
	if (empty) return __("Fill in {0}.", [__(plainLabel(empty.label || empty.fieldname))])
	if (uploading) return __("Wait for the file to finish uploading.")
	if (needsReceipt && !item.receipt) return __("Add the receipt for this item.")
	return ""
}
