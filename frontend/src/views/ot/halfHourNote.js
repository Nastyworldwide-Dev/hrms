//: The one plain sentence under the day list for an Overtime Pay claim: it is paid in half hours, so a
//: figure typed between them is cut DOWN ("1.37 becomes 1.0"). Owner ruling 5 Oct 2026. Said BEFORE the
//: person types, or the cut reads as a bug. Replacement Leave converts raw hours to days: no note.
export const halfHourNote = (isReplacementLeave, translate = (text) => text) =>
	isReplacementLeave ? "" : translate("Paid in half hours: 1.37 is saved as 1.0, 1.6 as 1.5.")

//: What a typed claim becomes (mirrors hrms.utils.ot_precision.half_hour_claim): rounded DOWN to the half
//: hour. Integer maths on halves, so a typed 1.5 stays 1.5.
export const halfHourClaim = (typed) => {
	const hours = Number(typed)
	if (!Number.isFinite(hours) || hours <= 0) return 0
	return Math.floor(hours * 2 + 1e-9) / 2
}
