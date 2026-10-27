import { personalCacheKey, sessionUser } from "@/utils/personalCache"
import { createResource, createListResource } from "frappe-ui"
import { setBadge } from "@/utils/appBadge"
import { useReloadOnGap } from "@/composables/realtime"

// No localStorage cache: this is a live counter. Caching it restored a stale
// non-zero value on load and lit the bell dot even after every notification was
// read/cleared server-side. initialData 0 + auto keeps the dot off until the
// server confirms genuinely-unread notifications.
export const unreadNotificationsCount = createResource({
	url: "hrms.api.get_unread_notifications_count",
	initialData: 0,
	auto: true,
	// The Home Screen icon carries the same number (alpha.7 §5.7).
	onSuccess: (count) => setBadge(count),
})

export const notifications = createListResource({
	doctype: "PWA Notification",
	// The cookie's user, not userResource.data: that read may have failed, and
	// reading .name off null here threw on import and hung every page (alpha.14).
	filters: { to_user: sessionUser() },
	fields: [
		"name",
		"from_user",
		"message",
		"read",
		"creation",
		"reference_document_type",
		"reference_document_name",
	],
	auto: false,
	cache: personalCacheKey("hrms:notifications"),
	orderBy: "creation desc",
	onSuccess() {
		unreadNotificationsCount.reload()
	},
})

export const arePushNotificationsEnabled = createResource({
	url: "hrms.api.are_push_notifications_enabled",
	cache: personalCacheKey("hrms:push_notifications_enabled"),
	auto: true,
})

// Single entry point to the push SDK's enable flow (browser permission ask +
// FCM token registration) — shared by the You page and PushNotificationPrompt.
// Resolves {permission_granted, token}; callers own their toasts/state.
export const enablePushNotifications = () => {
	console.info("[PushNotifications] Requesting push enable via SDK")
	return window.frappePushNotification.enableNotification()
}

// The socket's hrms:refetch_resource is a bonus, never the guarantee: a phone
// that put the app away misses it for good, and the bell and the cached feed
// stayed stale until a reload (27 Oct 2026). Catch up on the app's one "events
// may have been missed" moment: a socket reconnect, or back after a long hide.
// The bell, and the feed when a page of it was ever asked for (a list never
// fetched has nothing stale, and fetching it here would load it on every screen).
export function refreshNotifications(why) {
	console.info("[notifications] catching up:", why)
	unreadNotificationsCount.reload()
	if (notifications.list.fetched) notifications.reload()
}

useReloadOnGap(refreshNotifications)
