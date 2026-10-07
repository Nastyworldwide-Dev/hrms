// The app's one service worker: where it is registered, which push settings its address carries,
// and the two one-time moves for phones installed before alpha.12 (retire the old worker, move the
// push token to the app-root worker). Split out of main.js (alpha.41 S12): every update-bar fix
// touched this block beside unrelated app boot (b2f020a62, 6621d7bd9, b0811eab8). main.js calls
// registerAppWorker() once, after the router is ready.
//
// Relative imports with an extension, so the module loads under plain node and bun for its test.
import FrappePushNotification from "./frappe-push-notification.js"
import { setRegistration } from "../data/swRegistration.js"
import { workerURL } from "./workerURL.js"

//: Phones installed before alpha.12 carry a worker at /assets/hrms/frontend/
//: that never controlled the app. It is removed once the app-root worker is
//: registered, so it stops holding a stale precache and a second push path.
const OLD_WORKER_SCOPE = "/assets/hrms/frontend/"

async function retireOldWorker() {
	try {
		const registrations = await navigator.serviceWorker.getRegistrations()
		const old = registrations.filter((r) => new URL(r.scope).pathname === OLD_WORKER_SCOPE)
		await Promise.all(old.map((r) => r.unregister()))
		if (old.length) console.info("[sw] retired the pre-alpha.12 worker at", OLD_WORKER_SCOPE)
	} catch (error) {
		console.warn("[sw] could not retire the old worker:", error)
	}
}

//: A push token belongs to the worker it was made with. Someone who turned
//: notifications on before alpha.12 holds a token tied to the retired worker;
//: without this they would silently stop receiving notifications. Re-subscribe
//: on the app-root worker, once, only if they had push on.
const PUSH_MOVED_KEY = "hrms:push-moved-to-app-worker"

//: The push settings that last worked, so a slow or failed relay fetch does not
//: register a different worker address (utils/workerURL.js).
const PUSH_CONFIG_KEY = "hrms:push-config"

async function movePushToAppWorker() {
	const push = window.frappePushNotification
	try {
		if (!push?.isNotificationEnabled?.() || localStorage.getItem(PUSH_MOVED_KEY)) return
		if (typeof Notification === "undefined" || Notification.permission !== "granted") return
		push.token = null
		await push.enableNotification()
		localStorage.setItem(PUSH_MOVED_KEY, "1")
		console.info("[sw] push moved to the app-root worker")
	} catch (error) {
		console.warn("[sw] could not move push to the app-root worker:", error)
	}
}

export async function registerAppWorker() {
	window.frappePushNotification = new FrappePushNotification("hrms")

	if ("serviceWorker" in navigator) {
		// At the app root, not /assets/hrms/frontend/: a worker controls only pages
		// under its own folder, so from there it never controlled /hrms and the
		// app had no offline launch (alpha.12 C1). hrms/www/service_worker.py.
		// The SAME address every launch for the same settings (utils/workerURL.js):
		// a different address is a new worker to the browser, and the update bar
		// offered it on every launch (owner, 28 Sep 2026).
		let config = ""
		let stored = null
		try {
			stored = JSON.parse(localStorage.getItem(PUSH_CONFIG_KEY) || "null")
		} catch {
			stored = null
		}

		if (window.frappe?.boot?.push_relay_server_url) {
			try {
				config = await window.frappePushNotification.fetchWebConfig()
				try {
					localStorage.setItem(PUSH_CONFIG_KEY, JSON.stringify(config))
				} catch {
					// storage unavailable: the next launch fetches again, as before
				}
			} catch (err) {
				console.error("Failed to fetch FCM config; using the last good one", err)
			}
		}
		const serviceWorkerURL = workerURL("/hrms/sw.js", config || null, stored)

		navigator.serviceWorker
			.register(serviceWorkerURL, {
				type: "classic",
				scope: "/hrms",
			})
			.then((registration) => {
				setRegistration(registration)
				if (config || stored) {
					// fetchWebConfig returns this cached copy instead of the relay
					if (!config) window.frappePushNotification.webConfig = stored
					window.frappePushNotification.initialize(registration).then(() => {
						console.info("[sw] Frappe Push Notification initialized")
						return movePushToAppWorker()
					})
				}
				retireOldWorker()
			})
			.catch((err) => {
				console.error("Failed to register service worker", err)
			})
	} else {
		console.error("Service worker not enabled/supported by the browser")
	}
}
