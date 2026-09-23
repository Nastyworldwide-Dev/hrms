// A Check/Switch answers in the type it was given: Frappe's 0/1 stays a
// number, the app's own booleans stay booleans. Flipping 1 -> true would make
// an untouched form look edited.

/** @returns {boolean|number} `checked` in the shape of `current` */
export function toggleValue(current, checked) {
	return typeof current === "number" ? (checked ? 1 : 0) : Boolean(checked)
}
