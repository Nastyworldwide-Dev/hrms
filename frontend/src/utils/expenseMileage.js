// Mileage on an expense line (owner, 14 Oct 2026): HR sets a rate per km on
// the Expense Claim Type (or per company); staff type only the distance and
// see what they will claim. The server prices the line again on save
// (ExpenseClaim.set_mileage_amounts), so this is the preview, not the rule.

/** The amount for `km` at `rate`, rounded to cents; 0 for no or bad input. */
export function mileageAmount(km, rate) {
	const value = (parseFloat(km) || 0) * (parseFloat(rate) || 0)
	return value > 0 ? Math.round(value * 100) / 100 : 0
}

/**
 * The line's fields for a type with `rate` per km: the distance is asked and
 * required, the amount is shown read-only. No rate: the distance is not asked.
 */
export function withMileageFields(fields, rate) {
	return fields
		.filter((field) => rate > 0 || field.fieldname !== "distance_km")
		.map((field) => {
			if (!(rate > 0)) return field
			if (field.fieldname === "distance_km") return { ...field, reqd: 1, hidden: 0 }
			if (field.fieldname === "amount")
				return { ...field, read_only: 1, label: "You will claim", class: "g-form-row--claim" }
			return field
		})
}

/**
 * "70 km × RM 0.60 per km (Car)": how the amount was reached, under it.
 * `formatRate` writes the rate as money (formatCurrency with the claim's currency).
 */
export function mileageExplainer(km, rate, typeName, formatRate) {
	const value = parseFloat(km) || 0
	if (!(rate > 0) || !(value > 0)) return ""
	const kind = (typeName || "").split("·").pop().trim()
	const line = `${value} km × ${formatRate(rate)} per km`
	return kind ? `${line} (${kind})` : line
}
