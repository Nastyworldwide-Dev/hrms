//: The one plain sentence under the day list for an Overtime Pay claim: it is paid in half hours, so a
//: figure typed between them is cut DOWN ("1.37 becomes 1.0"). Owner ruling 5 Oct 2026. Said BEFORE the
//: person types, or the cut reads as a bug. Replacement Leave converts raw hours to days: no note.
export const halfHourNote = (isReplacementLeave, translate = (text) => text) =>
	isReplacementLeave ? "" : translate("Paid in half hours: 1.37 is saved as 1.0, 1.6 as 1.5.")
