import { createResource } from "frappe-ui"
import { employeeResource } from "./employee"
import { reactive } from "vue"

export const expenseClaimSummary = createResource({
	url: "hrms.api.get_expense_claim_summary",
	auto: true,
	cache: "hrms:expense_claim_summary",
})

const transformClaimData = (data) => {
	return data.map((claim) => {
		claim.doctype = "Expense Claim"
		return claim
	})
}

export const myClaims = createResource({
	url: "hrms.api.get_expense_claims",
	// Read per request, not once at module load: `employeeResource`
	// may not have resolved when this file is first imported, and a
	// captured `undefined` employee silently blanks the panel.
	makeParams() {
		return {
		employee: employeeResource.data?.name,
		limit: 10,
		}
	},
	auto: true,
	cache: "hrms:my_claims",
	transform(data) {
		return transformClaimData(data)
	},
	onSuccess() {
		expenseClaimSummary.reload()
	},
})

export const teamClaims = createResource({
	url: "hrms.api.get_expense_claims",
	// Read per request, not once at module load: `employeeResource`
	// may not have resolved when this file is first imported, and a
	// captured `undefined` employee silently blanks the panel.
	makeParams() {
		return {
		employee: employeeResource.data?.name,
		approver_id: employeeResource.data?.user_id,
		for_approval: 1,
		limit: 10,
		}
	},
	auto: true,
	cache: "hrms:team_claims",
	transform(data) {
		return transformClaimData(data)
	},
})

// decided by me — the approval trail Team Requests loses on decision
export const historyClaims = createResource({
	url: "hrms.api.get_expense_claims",
	// Read per request, not once at module load: `employeeResource`
	// may not have resolved when this file is first imported, and a
	// captured `undefined` employee silently blanks the panel.
	makeParams() {
		return {
		employee: employeeResource.data?.name,
		approver_id: employeeResource.data?.user_id,
		history: 1,
		limit: 10,
		}
	},
	auto: true,
	cache: "hrms:history_claims",
	transform(data) {
		return transformClaimData(data)
	},
})

export let claimTypesByID = reactive({})

export const claimTypesResource = createResource({
	url: "hrms.api.get_expense_claim_types",
	auto: true,
	transform(data) {
		return data.map((row) => {
			claimTypesByID[row.name] = row
			return row
		})
	},
})
