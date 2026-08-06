import { createResource, createListResource } from "frappe-ui"
import { userResource } from "./user"

// No localStorage cache: this is a live counter. Caching it restored a stale
// non-zero value on load and lit the bell dot even after every notification was
// read/cleared server-side. initialData 0 + auto keeps the dot off until the
// server confirms genuinely-unread notifications.
export const unreadNotificationsCount = createResource({
	url: "hrms.api.get_unread_notifications_count",
	initialData: 0,
	auto: true,
})

export const notifications = createListResource({
	doctype: "PWA Notification",
	filters: { to_user: userResource.data.name },
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
	cache: "hrms:notifications",
	orderBy: "creation desc",
	onSuccess() {
		unreadNotificationsCount.reload()
	},
})

export const arePushNotificationsEnabled = createResource({
	url: "hrms.api.are_push_notifications_enabled",
	cache: "hrms:push_notifications_enabled",
	auto: true,
})

// Single entry point to the push SDK's enable flow (browser permission ask +
// FCM token registration) — shared by AppSettings and PushNotificationPrompt.
// Resolves {permission_granted, token}; callers own their toasts/state.
export const enablePushNotifications = () => {
	console.info("[PushNotifications] Requesting push enable via SDK")
	return window.frappePushNotification.enableNotification()
}
