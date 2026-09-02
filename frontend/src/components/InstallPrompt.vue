<template>
	<!-- Install PWA dialog -->
	<GModal :is-open="showDialog" :title="__('Install Nadi')" @did-dismiss="dismiss">
		<p class="g-confirm__body">
			{{ __("Get the app on your device for easy access & a better experience!") }}
		</p>
		<GButton :label="__('Install')" @click="() => install()" />
	</GModal>

	<!-- iOS installation info message -->
	<Popover :show="iosInstallMessage" placement="bottom">
		<template #body>
			<div
				class="mt-[calc(100vh-15rem)] flex flex-col gap-3 mx-2 py-5 bg-accent-100 border border-accent-200 drop-shadow-xl"
			>
				<div class="flex flex-row text-center items-center justify-between mb-1 px-3">
					<span class="text-base text-inkbase font-extrabold">
						{{ __("Install Nadi") }}
					</span>
					<span class="inline-flex items-baseline">
						<FeatherIcon name="x" class="ml-auto h-4 w-4 text-ink-700" @click="dismiss" />
					</span>
				</div>
				<div class="text-xs text-ink-800 px-3">
					<span class="flex flex-col gap-2">
						<span>
							{{ __("Get the app on your iPhone for easy access & a better experience") }}
						</span>
						<span class="inline-flex items-start whitespace-nowrap">
							<span>Tap&nbsp;</span>
							<FeatherIcon name="share" class="h-4 w-4 text-accent-600" />
							<span>&nbsp;and then "Add to Home Screen"</span>
						</span>
					</span>
				</div>
			</div>
		</template>
	</Popover>
</template>

<script setup>
import GButton from "@/components/glass/GButton.vue"
import GModal from "@/components/glass/GModal.vue"
import { ref } from "vue"

import { Popover, FeatherIcon } from "frappe-ui"

import { INSTALL_DISMISS_KEY, isWithinCooldown } from "@/utils/installPromptMemory"
import { sessionUser } from "@/data/session"

// The prompt is for people using the app, not for the login screen — a sheet
// over the sign-in form is the wrong moment and obstructs "Forgot Password".
// Logging in triggers a full reload (see data/session.js), so gating on the
// session here is enough: the authed reload is where the prompt may appear.
const isAuthed = () => !!sessionUser()

// Initialize deferredPrompt for use later to show browser install prompt.
const deferredPrompt = ref(null)
const showDialog = ref(false)
const iosInstallMessage = ref(false)

// The install prompt is a bottom sheet that overlays the home content and the
// tab bar. `beforeinstallprompt` fires on every load while the app is
// installable, so without a memory of the user's dismissal it re-covered the
// navigation on every cold start and route back to home. Remember a dismissal
// and stay quiet for a cooldown; installing suppresses it for good. The
// cooldown predicate lives in installPromptMemory.js so it can be unit-tested.
function recentlyHandled() {
	try {
		return isWithinCooldown(localStorage.getItem(INSTALL_DISMISS_KEY), Date.now())
	} catch (e) {
		return false
	}
}

function dismiss() {
	showDialog.value = false
	iosInstallMessage.value = false
	try {
		localStorage.setItem(INSTALL_DISMISS_KEY, String(Date.now()))
	} catch (e) {
		// storage unavailable — the prompt may reappear next load, no worse than before
	}
}

const isIos = () => {
	// Detects if device is on iOS
	const userAgent = window.navigator.userAgent.toLowerCase()
	return /iphone|ipad|ipod/.test(userAgent)
}

// Detects if device is in standalone mode
const isInStandaloneMode = () => "standalone" in window.navigator && window.navigator.standalone

// Checks if should display install popup notification:
if (isIos() && !isInStandaloneMode() && !recentlyHandled() && isAuthed()) {
	iosInstallMessage.value = true
}

window.addEventListener("beforeinstallprompt", (e) => {
	// Prevent the mini-infobar from appearing on mobile
	e.preventDefault()
	// Stash the event so it can be triggered later.
	deferredPrompt.value = e
	// Honour a recent dismissal — the event fires on every load while
	// installable, and re-popping the sheet over the tab bar each time is the
	// nag this guard removes. Never surface it to a logged-out visitor.
	if (recentlyHandled() || !isAuthed()) return
	if (isIos() && !isInStandaloneMode()) {
		iosInstallMessage.value = true
	} else {
		showDialog.value = true
	}
})

window.addEventListener("appinstalled", () => {
	// Installed: never prompt again on this device.
	dismiss()
	deferredPrompt.value = null
})

// Only ever reached from the Install button's @click — browsers reject prompt()
// outside a user gesture, and the captured event is single-use, so it is dropped
// after firing rather than left to throw "already been used" on a second click.
async function install() {
	const prompt = deferredPrompt.value
	// Engaging with Install counts as handled — a cancelled native prompt must
	// not re-nag on the next load.
	dismiss()
	if (!prompt) return
	deferredPrompt.value = null
	try {
		await prompt.prompt()
	} catch (err) {
		console.warn("[InstallPrompt] Install prompt failed:", err?.message)
	}
}
</script>
