// Cost tags on an expense line: Cost Center plus every Accounting Dimension.
//
// hrms.api.get_doctype_fields drops each Link an Employee cannot read — Cost
// Center, Department, Branch, Location, Project — but keeps the "Accounting
// Dimensions" Section Break above them, so the New Expense Item sheet showed
// a header with nothing under it (15 Sep 2026). The choices come from
// hrms.api.get_expense_cost_tags instead, already fenced to the claim's
// company, and render as searchable selects (FormField's documentList path).

const SECTION = "accounting_dimensions_section"
const COLUMN = "dimension_col_break"

function tagField(fieldname, label, doctype, tag) {
	return {
		fieldname,
		fieldtype: "Link",
		label,
		options: doctype,
		documentList: tag.options,
		default: tag.default,
	}
}

/**
 * The sheet's fields with the cost-tag section rebuilt from `costTags`
 * ({cost_center: {default, options}, dimensions: [{fieldname, label,
 * document_type, default, options}]}). No tags, or none loaded yet: the
 * section is dropped rather than rendered empty.
 */
export function withCostTagFields(fields, costTags) {
	const dimensions = costTags?.dimensions || []
	const owned = new Set(["cost_center", ...dimensions.map((d) => d.fieldname)])
	const section = fields.find((f) => f.fieldname === SECTION)
	const kept = fields.filter(
		(f) => f.fieldname !== SECTION && f.fieldname !== COLUMN && !owned.has(f.fieldname)
	)

	const tagFields = []
	if (costTags?.cost_center?.options?.length) {
		tagFields.push(tagField("cost_center", "Cost Center", "Cost Center", costTags.cost_center))
	}
	for (const dim of dimensions) {
		if (dim.options?.length)
			tagFields.push(tagField(dim.fieldname, dim.label, dim.document_type, dim))
	}
	if (!tagFields.length) return kept

	return [
		...kept,
		{
			fieldname: SECTION,
			fieldtype: "Section Break",
			label: section?.label || "Accounting Dimensions",
		},
		...tagFields,
	]
}
