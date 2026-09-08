export const isChrome = () => navigator.userAgent.toLowerCase().includes("chrome")

export const showNotification = (payload) => {
	const registration = window.frappePushNotification.serviceWorkerRegistration
	if (!registration) return

	const notificationTitle = payload?.data?.title
	const notificationOptions = {
		body: payload?.data?.body || "",
	}
	if (payload?.data?.notification_icon) {
		notificationOptions["icon"] = payload.data.notification_icon
	}
	// The destination rides on data for EVERY browser: the worker's click
	// handler resolves data.url first, and a body tap carries no action. This
	// used to be Chrome-only, so a foreground notification on Firefox, Safari
	// or Samsung Internet opened nothing — the same gap the worker's own
	// background path closed on 2 Sep 2026. Non-Chrome keeps its explicit
	// action button as a second way in.
	notificationOptions["data"] = {
		url: payload?.data?.click_action,
	}
	if (!isChrome() && payload?.data?.click_action) {
		notificationOptions["actions"] = [
			{
				action: payload.data.click_action,
				title: "View Details",
			},
		]
	}

	registration.showNotification(notificationTitle, notificationOptions)
}
