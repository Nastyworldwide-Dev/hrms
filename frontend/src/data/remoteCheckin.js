import { createResource } from "frappe-ui"

export const submitRemarksResource = createResource({
	url: "nsty.api.remote_checkin.submit_remarks",
	auto: false,
})

export const pendingForApproverResource = createResource({
	url: "nsty.api.remote_checkin.list_pending_for_approver",
	cache: "nsty:remote-checkin-pending",
	auto: false,
})

export const pendingCountResource = createResource({
	url: "nsty.api.remote_checkin.get_pending_count",
	cache: "nsty:remote-checkin-pending-count",
	auto: false,
})

export const approveResource = createResource({
	url: "nsty.api.remote_checkin.approve",
	auto: false,
})

export const rejectResource = createResource({
	url: "nsty.api.remote_checkin.reject",
	auto: false,
})

export const openInSessionResource = createResource({
	url: "nsty.api.remote_checkin.get_open_in_session",
	cache: "nsty:remote-checkin-open-in",
	auto: false,
})

export const submitLateCheckoutResource = createResource({
	url: "nsty.api.remote_checkin.submit_late_checkout",
	auto: false,
})
