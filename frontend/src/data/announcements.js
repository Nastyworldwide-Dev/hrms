import { createResource } from "frappe-ui"

import { personalCacheKey } from "@/utils/personalCache"

// The announcement board (revamp §3). HR publishes in Desk; the PWA only ever
// reads, marks read, and acknowledges — all three about the session user, by
// construction, because no endpoint takes an employee argument.
//
// The cache key is PERSONAL. An announcement board is audience-filtered, so a
// shared key would serve one employee's department notices to the next person
// who signed in on the same device — which is exactly the case a shared phone
// in a factory makes routine.

export const homeAnnouncements = createResource({
	url: "hrms.api.announcements.home_announcements",
	cache: personalCacheKey("nsty:announcements-home"),
	auto: false,
})

export const allAnnouncements = createResource({
	url: "hrms.api.announcements.list_announcements",
	cache: personalCacheKey("nsty:announcements-all"),
	auto: false,
})

// NOT cached: opening a card is what marks it read, so a cached response would
// mean the second open never reaches the server and the read is never recorded
// for somebody who came back to re-read a policy.
export const announcementDetail = createResource({
	url: "hrms.api.announcements.get_announcement",
	auto: false,
})

export const acknowledgeAnnouncement = createResource({
	url: "hrms.api.announcements.acknowledge",
	auto: false,
})

/**
 * Re-read both boards after something changes what they say.
 *
 * Acknowledging moves a card out of the "needs you" slot on Home, and reading
 * one changes the unread count in two places — so both resources are stale
 * after either action, and refreshing only the one you are looking at leaves
 * the other wrong until a full reload.
 */
export async function reloadAnnouncements(reason = "change") {
	console.info("[announcements] reload", { reason })
	await Promise.all([
		homeAnnouncements.fetch()?.catch?.(() => {}),
		allAnnouncements.fetch()?.catch?.(() => {}),
	])
}
