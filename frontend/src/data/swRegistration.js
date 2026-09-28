// The app's ONE service worker registration, shared (28 Sep 2026). main.js
// registers /hrms/sw.js (with ?config=… when push is on) and hands the
// registration here; UpdatePrompt watches it. The prompt used to register the
// worker again through vite-plugin-pwa under a second URL, and the two kept
// replacing each other, so "A new version is ready" showed on every load.

import { ref } from "vue"

export const swRegistration = ref(null)

export function setRegistration(registration) {
	swRegistration.value = registration || null
	console.info("[sw] registration shared with the update prompt:", Boolean(registration))
}
