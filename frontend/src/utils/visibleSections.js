// Drop a Section Break that has no SHOWN field before the next one.
//
// Screens keep layout fields by kind (their allowlists name the data fields),
// so every Section Break of a doctype survives even when the allowlist removed
// everything under it. The New expense form rendered 6 empty headings.
//
// "Shown" mirrors FormField's showField: not hidden, and a read-only field only
// when it has a value. A Table renders through the form's own slot, so it counts.

const LAYOUT = new Set(["Section Break", "Column Break", "Tab Break"])

//: "<link>_name" beside its Link: the Link row already shows the title, so on
//: a read-only screen the name row says it twice (alpha.7 B5/B7).
function repeatsLink(field, fieldnames, readOnly) {
	const m = /^(.*)_name$/.exec(field.fieldname)
	return Boolean(m && fieldnames.has(m[1]) && readOnly(field))
}

export function isShown(field, model, readOnly = (f) => Boolean(f.read_only)) {
	if (LAYOUT.has(field.fieldtype)) return false
	if (field.fieldtype === "Table") return true
	if (field.hidden) return false
	const value = model?.[field.fieldname]
	if (readOnly(field) && (value == null || value === "")) return false
	return true
}

//: `readOnly(field)` is the form's own decision (FormView.isFieldReadOnly): a
//: sent request is read-only as a whole, not only its read_only fields.
export function dropEmptySections(fields, model, readOnly = (field) => Boolean(field.read_only)) {
	const out = []
	let pending = null // a Section Break waiting to prove it has content
	let dropped = 0
	const linkNames = new Set(fields.filter((x) => x.fieldtype === "Link").map((x) => x.fieldname))
	for (const field of fields) {
		if (repeatsLink(field, linkNames, readOnly)) continue
		if (field.fieldtype === "Section Break") {
			if (pending) dropped++
			pending = field
			continue
		}
		if (pending && isShown(field, model, readOnly)) {
			out.push(pending)
			pending = null
		}
		if (field.fieldtype === "Column Break" && pending) continue
		out.push(field)
	}
	if (pending) dropped++
	if (dropped) console.info("[visibleSections] dropped empty sections", dropped)
	return out
}
