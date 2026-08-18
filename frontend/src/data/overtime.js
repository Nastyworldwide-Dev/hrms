import { createResource } from "frappe-ui"
import { employeeResource } from "./employee"

import dayjs from "@/utils/dayjs"

// OT Request and Replacement Leave Claim were reachable only from their own
// "my" screens, so a manager had no queue for either — despite the API
// accepting `for_approval`, `hrms.overrides.ot_row_scope` granting reporting
// managers sight of their reports' rows, and RequestActionSheet already
// carrying an approve/submit branch for both doctypes. Only the resources that
// feed the Requests panel were missing.

const getOTDate = (row) => (row.ot_date ? dayjs(row.ot_date).format("D MMM") : "")

const transformOTRequests = (data) =>
	data.map((request) => {
		request.doctype = "OT Request"
		request.ot_date_label = getOTDate(request)
		return request
	})

const transformReplacementLeaveClaims = (data) =>
	data.map((claim) => {
		claim.doctype = "Replacement Leave Claim"
		claim.bank_month_label = claim.bank_month ? dayjs(claim.bank_month).format("MMMM YYYY") : ""
		return claim
	})

// Read per request, not once at module load: `employeeResource` may not have
// resolved when this file is first imported, and a captured `undefined`
// employee silently blanks the panel.
const own = () => ({ employee: employeeResource.data?.name, limit: 10 })
const forApproval = () => ({ ...own(), for_approval: 1 })

export const myOTRequests = createResource({
	url: "hrms.api.get_ot_requests",
	makeParams: own,
	auto: true,
	cache: "hrms:my_ot_requests",
	transform: transformOTRequests,
})

export const teamOTRequests = createResource({
	url: "hrms.api.get_ot_requests",
	makeParams: forApproval,
	auto: true,
	cache: "hrms:team_ot_requests",
	transform: transformOTRequests,
})

export const myReplacementLeaveClaims = createResource({
	url: "hrms.api.get_replacement_leave_claims",
	makeParams: own,
	auto: true,
	cache: "hrms:my_replacement_leave_claims",
	transform: transformReplacementLeaveClaims,
})

export const teamReplacementLeaveClaims = createResource({
	url: "hrms.api.get_replacement_leave_claims",
	makeParams: forApproval,
	auto: true,
	cache: "hrms:team_replacement_leave_claims",
	transform: transformReplacementLeaveClaims,
})
