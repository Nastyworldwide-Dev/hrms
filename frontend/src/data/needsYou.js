import { createResource } from "frappe-ui"

import { personalCacheKey } from "@/utils/personalCache"

// Everything waiting on this approver, across all seven request types
// (revamp slice B3).
//
// Home's "Needs you" block has shipped since 2.0 rendering ONE row type —
// remote check-in approvals — because this endpoint did not exist. An approver
// with four leave applications and an expense claim waiting saw nothing, which
// is worse than no block: it is a block that looks authoritative and is wrong.
//
// Personally cached, like every other approver-scoped read: the rows are
// whatever is routed to THIS person, so a shared key would show one approver's
// queue to the next person on the same device.

export const needsYouResource = createResource({
	url: "hrms.api.needs_you.get_needs_you",
	cache: personalCacheKey("nsty:needs-you"),
	auto: false,
})
