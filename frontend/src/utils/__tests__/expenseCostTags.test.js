// The New Expense Item sheet showed an "ACCOUNTING DIMENSIONS" header with
// nothing under it (15 Sep 2026): hrms.api.get_doctype_fields drops every
// Link an Employee cannot read (Cost Center, Department, Branch, Location,
// Project) but keeps the Section Break above them. The cost tags come back
// through hrms.api.get_expense_cost_tags instead — choices the server already
// fenced to the claim's company — and are rendered as searchable selects.
// Run: cd frontend && node --test src/utils/__tests__/expenseCostTags.test.js
import { test } from "node:test"
import assert from "node:assert/strict"

import { withCostTagFields } from "../expenseCostTags.js"

// what get_doctype_fields hands a bare Employee for Expense Claim Detail
const SERVER_FIELDS = [
	{ fieldname: "expense_date", fieldtype: "Date", label: "Expense Date" },
	{ fieldname: "expense_type", fieldtype: "Link", label: "Expense Claim Type", reqd: 1 },
	{ fieldname: "amount", fieldtype: "Currency", label: "Amount", reqd: 1 },
	{
		fieldname: "accounting_dimensions_section",
		fieldtype: "Section Break",
		label: "Accounting Dimensions",
	},
	{ fieldname: "dimension_col_break", fieldtype: "Column Break" },
]

const TAGS = {
	cost_center: {
		default: "Main - NW",
		options: [
			{ value: "Main - NW", label: "Main" },
			{ value: "Retail - NW", label: "Retail" },
		],
	},
	dimensions: [
		{
			fieldname: "branch",
			label: "Branch",
			document_type: "Branch",
			default: "KL",
			options: [{ value: "KL", label: "KL" }],
		},
	],
}

const names = (fields) => fields.map((f) => f.fieldname)

test("with no cost tags loaded the empty header is not rendered", () => {
	assert.deepEqual(names(withCostTagFields(SERVER_FIELDS, null)), [
		"expense_date",
		"expense_type",
		"amount",
	])
})

test("cost center and each dimension render under the section as searchable selects", () => {
	const fields = withCostTagFields(SERVER_FIELDS, TAGS)
	assert.deepEqual(names(fields), [
		"expense_date",
		"expense_type",
		"amount",
		"accounting_dimensions_section",
		"cost_center",
		"branch",
	])
	const costCenter = fields.find((f) => f.fieldname === "cost_center")
	assert.equal(costCenter.fieldtype, "Link")
	assert.equal(costCenter.label, "Cost Center", "keeps Frappe's label")
	assert.deepEqual(costCenter.documentList, TAGS.cost_center.options)
	assert.equal(costCenter.default, "Main - NW", "defaults from the employee / company")
	const branch = fields.find((f) => f.fieldname === "branch")
	assert.equal(branch.label, "Branch")
	assert.deepEqual(branch.documentList, [{ value: "KL", label: "KL" }])
	assert.equal(branch.default, "KL")
})

test("the section keeps the doctype's own label when the server sent it", () => {
	const section = withCostTagFields(SERVER_FIELDS, TAGS).find(
		(f) => f.fieldname === "accounting_dimensions_section"
	)
	assert.equal(section.fieldtype, "Section Break")
	assert.equal(section.label, "Accounting Dimensions")
})

test("a caller who CAN read Cost Center (HR) still gets one picker, not two", () => {
	const hrFields = [
		...SERVER_FIELDS,
		{ fieldname: "cost_center", fieldtype: "Link", label: "Cost Center", options: "Cost Center" },
	]
	const fields = withCostTagFields(hrFields, TAGS)
	assert.equal(fields.filter((f) => f.fieldname === "cost_center").length, 1)
	assert.ok(fields.find((f) => f.fieldname === "cost_center").documentList, "the fenced list wins")
})

test("no choices at all means no header either", () => {
	const empty = { cost_center: { default: null, options: [] }, dimensions: [] }
	assert.deepEqual(names(withCostTagFields(SERVER_FIELDS, empty)), [
		"expense_date",
		"expense_type",
		"amount",
	])
})
