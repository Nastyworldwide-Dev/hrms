// Which required rows are still empty, named as the screen names them
// (UX review 21 Oct 2026, F2). FormView's Send check and its per-row marks
// both read this, so the line by the button and the rows always agree.
import { plainLabel } from "./plainLabel.js"

/** An empty required table ([]) is missing too: `!value` alone missed it. */
export function isMissing(field, model) {
	if (!field.reqd || field.hidden) return false
	const value = model?.[field.fieldname]
	return Array.isArray(value) ? value.length === 0 : !value
}

/**
 * "" when nothing is missing; `__` is the app's translate (passed in so this runs in node).
 * `readOnly` is the form's own rule (FormView.isFieldReadOnly), so the line and the rows agree.
 */
export function missingHint(fields, model, __, readOnly = (field) => Boolean(field.read_only)) {
	const missing = (fields || []).filter((field) => isMissing(field, model))
	if (!missing.length) return ""
	// a row the person cannot fill (an approver set by HR) has no fix on this screen
	if (missing.some(readOnly))
		return __("Something this form needs is not set up for you. Ask HR.")
	const names = missing.map((field) => __(plainLabel(field.label || field.fieldname)))
	return __("Fill in {0}.", [names.join(", ")])
}
