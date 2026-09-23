// Doctype labels arrive in Title Case ("From Date", "Leave Type"); Glass and
// Apple HIG write field labels in sentence case ("From date"). Acronyms keep
// their capitals — "HR Approver" is "HR approver", never "Hr approver".
// An acronym is any word already written in capitals with 2+ letters (HR, IT,
// OT, ID, NRIC); a label that spells one "Hr" was wrong upstream and stays so.
// Runs on every field render, so it logs nothing: it is pure and cannot fail.

const keep = (w) => (w.length >= 2 && w === w.toUpperCase()) || /[a-z][A-Z]/.test(w)

const caseWord = (w, i) => (keep(w) ? w : i === 0 ? w[0].toUpperCase() + w.slice(1) : w.toLowerCase())

/** "Leave Type" -> "Leave type"; "HR Approver ID" -> "HR approver ID". */
export function sentenceCase(label) {
	if (!label || typeof label !== "string") return label ?? ""
	let i = 0
	return label.replace(/[A-Za-z][A-Za-z'’]*/g, (w) => caseWord(w, i++))
}
