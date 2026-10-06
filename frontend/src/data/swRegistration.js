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
//
// A NEW BUILD IS FOUND WHEN THE PERSON COMES BACK (6 Oct 2026). The browser
// looks for a new sw.js only on a page load and about once a day, so a phone
// that keeps Nadi in memory could run an old build for days after a deploy.
// So the app asks (registration.update()) at launch and whenever it becomes
// visible again. Asking never shows anything and never reloads: a build it
// finds still waits for the app to be out of sight, above.

import { ref } from "vue"

export const swRegistration = ref(null)

// At most one ask per 30 minutes, so flipping between apps all day is not a
// request to the server each time. A failed ask (offline) counts too.
// ceiling: 30 minutes, upgrade: a deploy needs to reach people faster than that
const CHECK_EVERY_MS = 30 * 60 * 1000
let lastCheckAt = 0

function applyWhenHidden() {
	const waiting = swRegistration.value?.waiting
	if (!waiting || document.visibilityState !== "hidden") return
	console.info("[sw] a new build is waiting and the app is hidden; letting it in")
	waiting.postMessage({ type: "SKIP_WAITING" })
}

// Never throws and never shows anything: offline, or a browser that refuses,
// is one console line and the app carries on with the build it has.
async function checkForNewBuild(why) {
	lastCheckAt = Date.now()
	console.info("[sw] asking for a new build:", why)
	try {
		await swRegistration.value?.update()
	} catch (error) {
		console.warn("[sw] could not check for a new build:", error)
	}
}

function onVisibilityChange() {
	applyWhenHidden()
	if (document.visibilityState !== "visible") return
	if (Date.now() - lastCheckAt < CHECK_EVERY_MS) {
		console.info("[sw] back in the app; asked less than 30 minutes ago, not asking again")
		return
	}
	checkForNewBuild("back in the app")
}

export function setRegistration(registration) {
	swRegistration.value = registration || null
	console.info("[sw] registration shared:", Boolean(registration))
	if (!registration) return
	document.addEventListener("visibilitychange", onVisibilityChange)
	registration.addEventListener("updatefound", () => {
		const worker = registration.installing
		worker?.addEventListener("statechange", () => {
			if (worker.state === "installed") applyWhenHidden()
		})
	})
	checkForNewBuild("launch")
}
