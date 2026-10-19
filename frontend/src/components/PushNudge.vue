<!--
  PushNudge — "Turn on notifications so you hear about the next one" (owner, 19 Oct 2026:
  nudge people who have not turned notifications on, on each announcement).

  A line beside the notice, never a sheet in the way of reading it. Shown only where pushes can
  work and are not on yet (utils/pushPrompt.js pushNudge); a browser that blocked them is told
  how to undo it, since no button can. Once turned on it disappears.
-->
<template>
	<GBanner v-if="kind" :variant="kind === 'blocked' ? 'warning' : 'info'" class="g-push-nudge">
		<template v-if="kind === 'ask'">
			<span>{{ __("Turn on notifications so you hear about the next announcement.") }}</span>
			<GButton
				class="g-btn--compact g-push-nudge__action"
				:label="__('Turn on')"
				:pending="enabling"
				:pending-label="__('Turning on…')"
				@click="enable"
			/>
		</template>
		<span v-else>
			{{
				__(
					"Notifications are blocked for Nadi. Allow them in your phone's settings for this app to hear about announcements."
				)
			}}
		</span>
	</GBanner>
</template>

<script setup>
import { computed, inject, ref } from "vue"

import GBanner from "@/components/glass/GBanner.vue"
import GButton from "@/components/glass/GButton.vue"
import { gToast } from "@/components/glass/toast"
import { arePushNotificationsEnabled, enablePushNotifications } from "@/data/notifications"
import { pushNudge } from "@/utils/pushPrompt"

const __ = inject("$translate")
const enabling = ref(false)
//: the SDK keeps no reactive state; re-read after a successful enable
const enabledNow = ref(false)

const kind = computed(() =>
	pushNudge({
		relayConfigured: Boolean(window.frappe?.boot?.push_relay_server_url),
		siteEnabled: Boolean(arePushNotificationsEnabled.data),
		alreadyEnabled:
			enabledNow.value || Boolean(window.frappePushNotification?.isNotificationEnabled?.()),
		notificationSupported: typeof window !== "undefined" && "Notification" in window,
		browserPermission: "Notification" in window ? Notification.permission : "unsupported",
	})
)

async function enable() {
	enabling.value = true
	try {
		const data = await enablePushNotifications()
		enabledNow.value = Boolean(data?.permission_granted)
		console.info("[PushNudge] enable", enabledNow.value ? "granted" : "refused")
		gToast(
			enabledNow.value
				? { title: __("Notifications on"), variant: "success" }
				: {
						title: __("Notifications not turned on"),
						text: __("Allow them in your phone's settings for this app."),
						variant: "info",
				  }
		)
	} catch (error) {
		// Push is optional: keep the detail in the console, say something calm (as PushNotificationPrompt)
		console.warn("[PushNudge] enable failed:", error?.message)
		gToast({
			title: __("Notifications not turned on"),
			text: __("Try again in a moment, or from You → Notifications."),
			variant: "info",
		})
	} finally {
		enabling.value = false
	}
}
</script>

<style>
.g-push-nudge {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 8px 12px;
}
.g-push-nudge__action {
	margin-left: auto;
}
</style>
