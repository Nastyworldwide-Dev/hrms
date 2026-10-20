// Why "Add expense" is dimmed, in words, or "" when it is not (alpha.60).
// The ONE rule: ExpensesTable dims Add exactly when this says something, so a
// dimmed button always has its reason (the #4855 class: a disabled Send that
// said nothing took three commits to cover; review of b7bb33cc9).
import { plainLabel } from "./plainLabel.js"

/**
 * `fields` are the doctype's fields: which are required (Add's old rule, kept).
 * `shown` are the rows the sheet draws: which one to name. `item` is the line.
 * `__` is the app's translate (passed in so this runs in node).
 */
export function addItemHint({ fields, shown, item, needsReceipt, uploading, loadFailed }, __) {
	if (loadFailed) return __("This form could not be loaded. Try again.")
	const isEmpty = (field) => field.reqd && !item[field.fieldname]
	if ((fields || []).some(isEmpty)) {
		// name a row the person can type in: a mileage amount is worked out from the
		// km, so it is the distance that is missing (review of 5b8da3417)
		const typeable = (shown || fields || []).find(
			(field) => isEmpty(field) && !field.read_only && !field.hidden
		)
		if (!typeable) return __("Fill in the required details.")
		// the row's own word ("Type", not "Expense Claim Type"), as FormField shows it
		return __("Fill in {0}.", [__(plainLabel(typeable.label || typeable.fieldname))])
	}
	if (uploading) return __("Wait for the file to finish uploading.")
	if (needsReceipt && !item.receipt) return __("Add the receipt for this item.")
	return ""
}
