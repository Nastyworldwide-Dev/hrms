import { createResource } from "frappe-ui"

import { personalCacheKey } from "@/utils/personalCache"

// The standing numbers the Requests screen states (revamp §5).
//
// One call rather than four: the leave balance, the unclaimed overtime, the
// unpaid expenses and the unmarked days each already have an endpoint, and
// the screen would otherwise wait on all of them in series before it could
// draw anything.
//
// Personally cached — every figure is about the session user's own record.

export const requestsSummary = createResource({
	url: "hrms.api.requests_summary.get_requests_summary",
	cache: personalCacheKey("nsty:requests-summary"),
	auto: false,
})
