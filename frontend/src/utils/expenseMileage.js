// Mileage on an expense line (owner, 14 Oct 2026): HR sets a rate per km on
// the Expense Claim Type (or per company); staff type only the distance and
// see what they will claim. The server prices the line again on save
// (ExpenseClaim.set_mileage_amounts), so this is the preview, not the rule.

/** The amount for `km` at `rate`, rounded to cents; 0 for no or bad input. */
export function mileageAmount(km, rate) {
	const value = (parseFloat(km) || 0) * (parseFloat(rate) || 0)
	return value > 0 ? Math.round(value * 100) / 100 : 0
}

// ponytail: a type is "mileage" by its name; add a type flag when a mileage
// type is named otherwise. Live has "Mileage (CAR)" and "Mileage (Motorcycle)".
const isMileageType = (typeName) => /mileage/i.test(typeName || "")

/**
 * The line's fields for a type with `rate` per km: the distance is asked and
 * required, the amount is shown read-only. A mileage type with no rate yet
 * still asks the distance, and the amount stays typed. Otherwise no distance.
 */
export function withMileageFields(fields, rate, typeName) {
	const asksKm = rate > 0 || isMileageType(typeName)
	return fields
		.filter((field) => asksKm || field.fieldname !== "distance_km")
		.map((field) => {
			if (field.fieldname === "distance_km" && asksKm)
				return { ...field, reqd: rate > 0 ? 1 : 0, hidden: 0 }
			if (!(rate > 0)) return field
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

/** Why a mileage line is not priced: HR has not set its rate yet (never silent). */
export function missingRateNote(rate, typeName, __ = (text) => text) {
	return !(rate > 0) && isMileageType(typeName)
		? __("HR has not set a rate for this type yet. Type the amount.")
		: ""
}
