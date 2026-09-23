import { createResource } from "frappe-ui"

import { personalCacheKey } from "@/utils/personalCache"

// Home's "This week" and "Coming up" blocks (owner-approved Home, 23 Sep
// 2026). Both endpoints read the session user's own employee only, so the
// cache key is PERSONAL: on a shared phone the next person must never see the
// previous person's week or their booked leave.

export const homeWeek = createResource({
	url: "hrms.api.home.get_home_week",
	cache: personalCacheKey("nsty:home-week"),
	auto: false,
})

export const homeComingUp = createResource({
	url: "hrms.api.home.get_home_coming_up",
	cache: personalCacheKey("nsty:home-coming-up"),
	auto: false,
})
