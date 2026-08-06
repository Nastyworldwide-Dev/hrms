// Decision logic for the push-notification soft-ask shown on app open.
// Pure (no window access except via injected storage) so it stays testable
// with node --test — the Vue component builds the context and calls these.

export const DECLINE_KEY = "hrms:push_prompt_declined"

export const hasDeclined = (storage = window.localStorage) =>
	storage.getItem(DECLINE_KEY) !== null

export const recordDecline = (storage = window.localStorage) => {
	console.info("[PushPrompt] User declined push notifications on this device")
	storage.setItem(DECLINE_KEY, new Date().toISOString())
}

export const shouldShowPushPrompt = ({
	relayConfigured,
	siteEnabled,
	alreadyEnabled,
	notificationSupported,
	browserPermission,
	declined,
	sdkInitialized,
}) =>
	Boolean(
		relayConfigured &&
			siteEnabled &&
			!alreadyEnabled &&
			notificationSupported &&
			browserPermission !== "denied" &&
			!declined &&
			sdkInitialized
	)
