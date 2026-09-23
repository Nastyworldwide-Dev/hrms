import { createResource } from "frappe-ui"

import { personalCacheKey } from "@/utils/personalCache"

// The Requests panel's filter chip counts, over EVERY one of my requests.
// The chips used to count the rows already loaded — the newest ten of each
// type — so the numbers were only true for someone with few requests
// (audit P0-8). Server rule mirrors utils/requestStatus.js.
export const myRequestCounts = createResource({
	url: "hrms.api.request_counts.get_my_request_counts",
	auto: true,
	cache: personalCacheKey("hrms:my_request_counts"),
})
