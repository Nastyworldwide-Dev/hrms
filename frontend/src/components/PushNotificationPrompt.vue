<template>
	<ion-modal
		:is-open="isOpen"
		@didDismiss="onDismiss"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
	>
		<div class="bg-ground w-full flex flex-col pb-8 border-t-[3px] border-inkbase">
			<div class="w-full flex flex-col gap-1 pt-6 pb-4 bg-ground px-4">
				<div class="m-kicker">
					{{ step === 1 ? __("Notifications") : __("Are you sure?") }}
				</div>
				<span class="text-inkbase font-extrabold text-[22px] leading-tight">
					{{ step === 1 ? __("Don't miss an update") : __("Stay in the loop?") }}
				</span>
				<span class="text-xs text-ink-600">
					{{
						step === 1
							? __(
									"Turn on push notifications so you know the moment something needs you — no need to keep checking the app."
								)
							: __(
									"Without notifications you won't know when your leave is approved or when you forget to check out. You can turn them on anytime in Settings → Notifications — we won't ask again."
								)
					}}
				</span>
			</div>

			<div v-if="step === 1" class="w-full flex flex-col px-4 gap-2">
				<div
					v-for="benefit in benefits"
					:key="benefit"
					class="flex items-center gap-2.5 bg-surface border border-divider px-3 py-2.5 text-xs font-semibold text-inkbase"
				>
					<span class="w-2 h-2 bg-accent-500 shrink-0" />
					{{ benefit }}
				</div>
			</div>

			<div class="flex flex-col gap-2 px-4 pt-4">
				<button
					class="w-full bg-accent text-ground border-none px-3.5 py-3 font-sans font-extrabold text-[13px] cursor-pointer text-left hover:bg-accent-600 disabled:opacity-60 flex justify-between items-center"
					@click="enable"
					:disabled="enabling"
				>
					<span>{{ enabling ? __("Enabling…") : __("Enable Notifications") }}</span>
					<span aria-hidden="true">→</span>
				</button>
				<button
					class="w-full bg-transparent text-ink-700 px-3.5 py-2.5 font-sans font-extrabold text-xs uppercase tracking-wide cursor-pointer hover:text-inkbase disabled:opacity-60"
					@click="decline"
					:disabled="enabling"
				>
					{{ step === 1 ? __("Not now") : __("No thanks, don't ask again") }}
				</button>
			</div>
		</div>
	</ion-modal>
</template>

<script setup>
import { inject, onMounted, ref } from "vue"
import { IonModal } from "@ionic/vue"
import { toast } from "frappe-ui"

import {
	arePushNotificationsEnabled,
	enablePushNotifications,
} from "@/data/notifications"
import {
	hasDeclined,
	recordDecline,
	shouldShowPushPrompt,
} from "@/utils/pushPrompt"

const __ = inject("$translate")

const isOpen = ref(false)
const step = ref(1)
const enabling = ref(false)
// set once the user has answered (enabled, blocked, or declined) so a
// programmatic close isn't mistaken for a swipe-away in onDismiss
let decided = false

const benefits = [
	__("Your leave & requests — approved or rejected"),
	__("Forgot-to-check-out reminders"),
	__("Approvals waiting for your action"),
]

// The push SDK initializes async after service-worker registration (main.js);
// enabling before that would fail, so the prompt waits for it.
const waitForSdkInit = async (timeoutMs = 10000, intervalMs = 400) => {
	console.info("[PushPrompt] Waiting for push SDK initialization")
	const start = Date.now()
	while (Date.now() - start < timeoutMs) {
		if (window.frappePushNotification?.initialized) return true
		await new Promise((resolve) => setTimeout(resolve, intervalMs))
	}
	return false
}

onMounted(async () => {
	const sdkInitialized = await waitForSdkInit()
	try {
		// site-level flag may still be loading on a cold start
		await arePushNotificationsEnabled.promise
	} catch (error) {
		console.warn("[PushPrompt] Failed to fetch site push flag", error)
	}
	const context = {
		relayConfigured: Boolean(window.frappe?.boot?.push_relay_server_url),
		siteEnabled: Boolean(arePushNotificationsEnabled.data),
		alreadyEnabled: Boolean(
			window.frappePushNotification?.isNotificationEnabled()
		),
		notificationSupported: "Notification" in window,
		browserPermission:
			"Notification" in window ? Notification.permission : "unsupported",
		declined: hasDeclined(),
		sdkInitialized,
	}
	if (!shouldShowPushPrompt(context)) {
		console.info("[PushPrompt] Auto-prompt skipped", context)
		return
	}
	// small grace so the sheet doesn't fight the page-load transition
	setTimeout(() => (isOpen.value = true), 1200)
})

const enable = () => {
	enabling.value = true
	enablePushNotifications()
		.then((data) => {
			decided = true
			isOpen.value = false
			if (data.permission_granted) {
				toast({
					title: __("Success"),
					text: __("Notifications enabled — you're all set"),
					icon: "check-circle",
					position: "bottom-center",
					iconClasses: "text-green-500",
				})
			} else {
				toast({
					title: __("Error"),
					text: __(
						"Blocked by the browser — allow notifications for this site in your browser settings, then retry from Settings → Notifications"
					),
					icon: "alert-circle",
					position: "bottom-center",
					iconClasses: "text-red-500",
				})
			}
		})
		.catch((error) => {
			decided = true
			isOpen.value = false
			toast({
				title: __("Error"),
				text: __(error.message),
				icon: "alert-circle",
				position: "bottom-center",
				iconClasses: "text-red-500",
			})
		})
		.finally(() => {
			enabling.value = false
		})
}

const decline = () => {
	if (step.value === 1) {
		step.value = 2
		return
	}
	decided = true
	recordDecline()
	isOpen.value = false
	toast({
		title: __("Okay"),
		text: __("Enable anytime in Settings → Notifications"),
		icon: "info",
		position: "bottom-center",
		iconClasses: "text-ink-600",
	})
}

const onDismiss = () => {
	if (decided) return
	// swiping away the soft ask counts as "Not now" → escalate once to the
	// confirm step; swiping away the confirm step records nothing, so the
	// prompt returns on the next app open
	if (step.value === 1) {
		step.value = 2
		setTimeout(() => (isOpen.value = true), 150)
	} else {
		isOpen.value = false
	}
}
</script>
