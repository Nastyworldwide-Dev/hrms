import { createResource } from "frappe-ui"

export const submitRemarksResource = createResource({
	url: "hrms.api.remote_checkin.submit_remarks",
	auto: false,
})

export const pendingForApproverResource = createResource({
	url: "hrms.api.remote_checkin.list_pending_for_approver",
	cache: "nsty:remote-checkin-pending",
	auto: false,
})

export const decidedForApproverResource = createResource({
	url: "hrms.api.remote_checkin.list_decided_for_approver",
	auto: false,
})

export const pendingCountResource = createResource({
	url: "hrms.api.remote_checkin.get_pending_count",
	cache: "nsty:remote-checkin-pending-count",
	auto: false,
})

export const approveResource = createResource({
	url: "hrms.api.remote_checkin.approve",
	auto: false,
})

export const rejectResource = createResource({
	url: "hrms.api.remote_checkin.reject",
	auto: false,
})

export const submitLateCheckoutResource = createResource({
	url: "hrms.api.remote_checkin.submit_late_checkout",
	auto: false,
})
