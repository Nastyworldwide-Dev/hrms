// The app's ONE service worker registration (28 Sep 2026). main.js registers
// /hrms/sw.js (with ?config=… when push is on) and hands the registration here.
// Never register it a second time: two URLs are two workers, and they replace
// each other on every load.
//
// A NEW BUILD TAKES OVER QUIETLY (owner, 30 Sep 2026: "remove the new update
// popup, because we dont really need that"). The "A new version is ready" bar
// is gone. A downloaded build still never takes the page under a half-written
// form: it is let in only while the app is out of sight (switched away, phone
// locked). Nothing reloads; the next screen opened is the new build, and a
// chunk the old page can no longer find reloads itself (router/stale-chunk.js).

import { ref } from "vue"

export const swRegistration = ref(null)

function applyWhenHidden() {
	const waiting = swRegistration.value?.waiting
	if (!waiting || document.visibilityState !== "hidden") return
	console.info("[sw] a new build is waiting and the app is hidden; letting it in")
	waiting.postMessage({ type: "SKIP_WAITING" })
}

export function setRegistration(registration) {
	swRegistration.value = registration || null
	console.info("[sw] registration shared:", Boolean(registration))
	if (!registration) return
	document.addEventListener("visibilitychange", applyWhenHidden)
	registration.addEventListener("updatefound", () => {
		const worker = registration.installing
		worker?.addEventListener("statechange", () => {
			if (worker.state === "installed") applyWhenHidden()
		})
	})
}
