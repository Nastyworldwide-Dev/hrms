<template>
	<!-- On the kit (owner, 25 Sep 2026: old hand-drawn sheets): what you get is
	     a group of rows, the ask is the kit's one primary button, "not now" the
	     plain one. -->
	<GModal :is-open="isOpen" :title="sheetTitle" @did-dismiss="onDismiss">
		<div class="g-form-body">
			<section class="g-form-section">
				<div v-if="step === 1" class="g-form-group">
					<div v-for="benefit in benefits" :key="benefit" class="g-form-row g-form-row--readonly">
						<span class="g-form-row__label">{{ benefit }}</span>
					</div>
				</div>
				<p class="g-form-footer">
					{{
						step === 1
							? __(
									"Turn on push notifications so you know the moment something needs you — no need to keep checking the app."
							  )
							: __(
									"Without notifications you won't know when your leave is approved or when you forget to check out. You can turn them on anytime in Settings → Notifications — we won't ask again."
							  )
					}}
				</p>
			</section>

			<div class="flex flex-col gap-3">
				<GButton :label="__('Turn on notifications')" :pending="enabling" :disabled="enabling" @click="enable" />
				<GGhostButton
					:label="step === 1 ? __('Not now') : __('No thanks, don\'t ask again')"
					:disabled="enabling"
					@click="decline"
				/>
			</div>
		</div>
	</GModal>
</template>

<script setup>
import GModal from "@/components/glass/GModal.vue"
import GButton from "@/components/glass/GButton.vue"
import GGhostButton from "@/components/glass/GGhostButton.vue"
import { computed, inject, onMounted, onUnmounted, ref } from "vue"
import { gToast } from "@/components/glass/toast"

import { arePushNotificationsEnabled, enablePushNotifications } from "@/data/notifications"
import {
	escalatesOnDismiss,
	hasDeclined,
	recordDecline,
	shouldShowPushPrompt,
} from "@/utils/pushPrompt"

const __ = inject("$translate")

const isOpen = ref(false)
const step = ref(1)
const sheetTitle = computed(() =>
	step.value === 1 ? __("Don't miss an update") : __("Stay in the loop?")
)
const enabling = ref(false)
// set once the user has answered (enabled, blocked, or declined) so a
// programmatic close isn't mistaken for a swipe-away in onDismiss
let decided = false
// the eligibility chain and reopen timer outlive quick Home visits; this
// keeps them from touching refs on a dead component instance
let unmounted = false
onUnmounted(() => {
	unmounted = true
})

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
	while (!unmounted && Date.now() - start < timeoutMs) {
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
		alreadyEnabled: Boolean(window.frappePushNotification?.isNotificationEnabled()),
		notificationSupported: "Notification" in window,
		browserPermission: "Notification" in window ? Notification.permission : "unsupported",
		declined: hasDeclined(),
		sdkInitialized,
	}
	if (unmounted || !shouldShowPushPrompt(context)) {
		console.info("[PushPrompt] Auto-prompt skipped", context)
		return
	}
	// small grace so the sheet does not open while the check-in sheet that led
	// here is still closing (it mounts after a successful check-in, Home plan H7)
	setTimeout(() => {
		if (!unmounted) isOpen.value = true
	}, 1200)
})

const enable = () => {
	// answered as soon as the tap lands: a swipe-away while the permission
	// ask is in flight must not re-escalate the sheet
	decided = true
	enabling.value = true
	enablePushNotifications()
		.then((data) => {
			isOpen.value = false
			if (data.permission_granted) {
				gToast({
					title: __("Success"),
					text: __("Notifications enabled — you're all set"),
					variant: "success",
				})
			} else {
				gToast({
					title: __("Error"),
					text: __(
						"Blocked by the browser — allow notifications for this site in your browser settings, then retry from Settings → Notifications"
					),
					variant: "error",
				})
			}
		})
		.catch((error) => {
			isOpen.value = false
			// Push is a nice-to-have. The raw failure ("Failed to subscribe to push
			// notification", thrown when the backend token registration returns false)
			// is unactionable AND lands as a red Error on the home screen — which is
			// exactly what alarmed the senior. Keep the detail in the console; tell the
			// user something calm and optional instead.
			console.warn("[PushPrompt] enable failed:", error?.message)
			gToast({
				title: __("Notifications not turned on"),
				text: __(
					"We couldn't turn on notifications right now — you can try again anytime in Settings → Notifications."
				),
				variant: "info",
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
	gToast({
		title: __("Okay"),
		text: __("Enable anytime in Settings → Notifications"),
		variant: "info",
	})
}

const onDismiss = () => {
	// Ionic dismisses the overlay without writing back to the one-way
	// :is-open binding — reset the ref first, or the reopen assignment
	// below is an Object.is no-op and the confirm step never shows
	const escalate = escalatesOnDismiss(step.value, decided)
	isOpen.value = false
	if (!escalate) return
	step.value = 2
	setTimeout(() => {
		if (!unmounted) isOpen.value = true
	}, 150)
}
</script>
