import { createResource } from "frappe-ui"

import { personalCacheKey } from "@/utils/personalCache"

// The calendar's two reads (revamp §4).
//
// THE GRID CARRIES DOTS, THE DAY SHEET CARRIES WORDS. `monthFlags` is the
// small per-date payload a 44px tile can draw; `daySheet` is the sentences,
// fetched only when somebody taps. That split is what keeps a month view from
// loading every punch, every leave application and every roster line for
// thirty days at once.

export const monthFlags = createResource({
	url: "hrms.api.calendar.get_month_flags",
	cache: personalCacheKey("nsty:calendar-flags"),
	auto: false,
})

// NOT cached. The sheet is per date and per persona, and a cache keyed on the
// resource rather than the date would serve yesterday's sheet for today.
export const daySheet = createResource({
	url: "hrms.api.calendar.get_day",
	auto: false,
})
