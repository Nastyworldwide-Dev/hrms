import { personalCacheKey } from "@/utils/personalCache"
import { createResource } from "frappe-ui"

// Native Helpdesk (v16.23.0): every call goes through hrms.api.helpdesk, which
// defers to the Helpdesk app's own permission model and adds raised_by_name.

// nav gate: More / SideNav show the Helpdesk entry only where the app exists.
// A site without Helpdesk (nasty-live) returns false and nothing else changes.
export const helpdeskAvailable = createResource({
	url: "hrms.api.helpdesk.is_available",
	auto: true,
	cache: personalCacheKey("hrms:helpdesk_available"),
	onError(error) {
		console.warn("[helpdesk] availability probe failed:", error?.messages?.[0] || error)
	},
})

export const myTickets = createResource({
	url: "hrms.api.helpdesk.list_tickets",
	cache: personalCacheKey("hrms:helpdesk_tickets"),
	onError(error) {
		console.warn("[helpdesk] ticket list failed:", error?.messages?.[0] || error)
	},
})

export const ticketOptions = createResource({
	url: "hrms.api.helpdesk.get_options",
	cache: personalCacheKey("hrms:helpdesk_options"),
})

export const newTicket = createResource({
	url: "hrms.api.helpdesk.new_ticket",
})

export const replyToTicket = createResource({
	url: "hrms.api.helpdesk.reply",
})

// per-ticket read; params set by the detail view before fetch
export const ticketDetail = createResource({
	url: "hrms.api.helpdesk.get_ticket",
	onError(error) {
		console.warn("[helpdesk] ticket read failed:", error?.messages?.[0] || error)
	},
})
