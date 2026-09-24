// The Home Screen icon badge (alpha.7 §5.7): the unread count, the same
// number as the bell's dot. Badging API; iOS 16.4+ in Home Screen apps.
// Where it is missing or refused, nothing happens.
export async function setBadge(count, nav = globalThis.navigator) {
	const n = Number(count) || 0
	try {
		if (n > 0 && nav?.setAppBadge) await nav.setAppBadge(n)
		else if (nav?.clearAppBadge) await nav.clearAppBadge()
	} catch (error) {
		console.info("[appBadge] not set:", error?.message)
	}
}
