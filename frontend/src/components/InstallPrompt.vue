<template>
	<!-- Install PWA dialog -->
	<GModal :is-open="showDialog" :title="__('Install Nadi')" @did-dismiss="dismiss">
		<p class="g-confirm__body">
			{{ __("Get the app on your device for easy access & a better experience!") }}
		</p>
		<GButton :label="__('Install')" @click="() => install()" />
	</GModal>

	<!-- iPhone Safari: no prompt exists; Home shows InstallHint instead (alpha.7 0.10). -->
</template>

<script setup>
import GButton from "@/components/glass/GButton.vue"
import GModal from "@/components/glass/GModal.vue"
import { ref } from "vue"

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
	try {
		localStorage.setItem(INSTALL_DISMISS_KEY, String(Date.now()))
	} catch (e) {
		// storage unavailable — the prompt may reappear next load, no worse than before
	}
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
	showDialog.value = true
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
