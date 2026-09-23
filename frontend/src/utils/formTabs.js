// Cut a doctype's field list into the form's tabs, each ending at its
// `lastField`.
//
// A boundary that is not in the list (filtered out by a screen's allowlist,
// renamed in Desk) used to produce findIndex -1 and an EMPTY tab: on 22 Sep the
// expense form lost `taxes` and every new claim rendered no fields at all
// (audit P0-1). A missing boundary now closes the tab at the end of the list,
// so a tab can lose its edge but never its fields.
export function splitFieldsByTab(fields, tabs) {
	const byTab = {}
	let start = 0
	for (const tab of tabs || []) {
		const found = fields.findIndex((field) => field.fieldname === tab.lastField)
		if (found === -1) {
			console.warn("[formTabs] tab boundary not in the field list", tab.name, tab.lastField)
		}
		const end = found === -1 || found < start ? fields.length : found + 1
		byTab[tab.name] = fields.slice(start, end)
		start = end
	}
	return byTab
}
