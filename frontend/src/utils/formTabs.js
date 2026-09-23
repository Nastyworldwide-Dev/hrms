// Cut a doctype's field list into the form's tabs, each ending at its
// `lastField`.
//
// A boundary that is not in the list (filtered out by a screen's allowlist,
// renamed in Desk) used to produce findIndex -1 and an EMPTY tab: on 22 Sep the
// expense form lost `taxes` and every new claim rendered no fields at all
// (audit P0-1). Now a tab whose boundary is missing (or points backwards)
// takes the rest of the list when no later tab has a real boundary, and
// otherwise yields to the next tab that does. Every field lands in exactly one
// tab, and a missing boundary can never empty the tabs after it.
export function splitFieldsByTab(fields, tabs) {
	const list = tabs || []
	const ends = list.map(
		(tab) => fields.findIndex((field) => field.fieldname === tab.lastField) + 1
	)
	const byTab = {}
	let start = 0
	list.forEach((tab, i) => {
		let end = ends[i]
		if (end <= start) {
			console.warn("[formTabs] tab boundary not in the field list", tab.name, tab.lastField)
			const laterIsReal = ends.slice(i + 1).some((later) => later > start)
			end = laterIsReal ? start : fields.length
		}
		byTab[tab.name] = fields.slice(start, end)
		start = end
	})
	return byTab
}
