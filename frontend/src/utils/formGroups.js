// A doctype's flat field list -> the groups of an inset grouped form.
//
// Each Section Break starts a group under its label; Column Breaks (a Desk
// grid) vanish; a Table is its own segment, because it draws its own list, and
// it splits the rows around it. Empty groups are dropped (visibleSections has
// already removed headings with nothing shown under them).

//: `shown(field)` says whether a row actually draws (FormView passes its own
//: rule), so a one-row section is judged by what the person sees.
export function groupFields(fields, shown = (f) => !f.hidden) {
	const groups = []
	let current = { key: "top", label: "", segments: [] }
	const push = () => {
		if (current.segments.length) groups.push(current)
	}
	const rows = () => {
		const last = current.segments[current.segments.length - 1]
		if (last?.kind === "rows") return last.fields
		const seg = { kind: "rows", fields: [] }
		current.segments.push(seg)
		return seg.fields
	}
	for (const field of fields || []) {
		if (field.fieldtype === "Section Break") {
			push()
			current = { key: field.fieldname, label: field.label || "", segments: [] }
		} else if (field.fieldtype === "Table") {
			current.segments.push({ kind: "table", field })
		} else if (field.fieldtype !== "Column Break" && field.fieldtype !== "Tab Break") {
			rows().push(field)
		}
	}
	push()
	// A one-row section keeps no header (alpha.7 B13): the row's label names it.
	for (const g of groups) {
		const only = g.segments.length === 1 && g.segments[0].kind === "rows" ? g.segments[0].fields : null
		if (only && only.filter(shown).length === 1) g.label = ""
	}
	return groups
}
