import { personalCacheKey } from "@/utils/personalCache"
import { createResource } from "frappe-ui"

// Which sibling apps this person is offered: keys from the server, which
// holds the role rule (hrms.api.app_links; audit F-15).
export const myApps = createResource({
	url: "hrms.api.app_links.get_my_apps",
	cache: personalCacheKey("hrms:apps_offered"),
	auto: true,
})
