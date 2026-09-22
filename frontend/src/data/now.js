import { createResource } from "frappe-ui"

import { personalCacheKey } from "@/utils/personalCache"

// What is true right now (revamp §2).
//
// Home's first line said "Last check-out was at 08:17 pm" and left the reader
// to work out everything else: am I on shift, have I been in six hours or
// nine, does today's shift even start yet. One call, because Home already
// makes several and a fourth spinner at the top of the first screen is the
// worst place to add latency.

export const nowResource = createResource({
	url: "hrms.api.now.get_now",
	cache: personalCacheKey("nsty:now"),
	auto: false,
})
