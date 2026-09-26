// FIRST import, before anything that can declare an auto resource — see the
// comment inside; moving it below App.vue re-breaks the Team feature.
import "./resourceConfig"

import { createApp } from "vue"
import App from "./App.vue"
import router from "./router"
import { initSocket } from "./socket"

import { resourcesPlugin, frappeRequest } from "frappe-ui"
import { translationsPlugin } from "./plugins/translationsPlugin.js"
import ResourceError from "@/components/ResourceError.vue"
import { applyProductName } from "@/utils/productName"
import { blockZoom } from "@/utils/blockZoom"
import { noOverscroll } from "@/utils/noOverscroll"
import { keyboardSafe } from "@/utils/keyboardSafe"

import { IonicVue } from "@ionic/vue"

import { session } from "@/data/session"
import { userResource } from "@/data/user"
import { employeeResource } from "@/data/employee"

import dayjs from "@/utils/dayjs"
import { lockPortraitOnPhones } from "@/utils/orientationLock"
import { decideNavigation } from "@/router/navigationGate"
import getIonicConfig from "@/utils/ionicConfig"
import { employeeGate } from "@/utils/identity"

import FrappePushNotification from "@/utils/frappe-push-notification"

/* Core CSS required for Ionic components to work properly */
import "@ionic/vue/css/core.css"

/* Theme variables */
import "./theme/variables.css"

import "./main.css"
/* Glass theme (generated, see design/tokens.json). Modernist was retired in
   phase 3.4; theme/variables.css stays for Ionic's --ion-color-* ramps only
   (spec §16.3), and glass.variables.css overrides the three that map. */
import "./theme/fonts.css"
import "./theme/glass.css"
import "./theme/glass.variables.css"
import "./theme/glass-components.css"
import "./data/theme"
import { installDiagnostics } from "@/utils/diagnostics"

// Zoom off (owner ruling, 25 Sep 2026); see utils/blockZoom.js.
blockZoom()
noOverscroll()
keyboardSafe()
const app = createApp(App)

// FIRST, before any plugin: a failure while the app is still starting is
// exactly the one nobody can reproduce, and the seam has to exist before the
// thing that might throw.
installDiagnostics(app)
const socket = initSocket()

// The resourceFetcher config lives in ./resourceConfig, imported FIRST —
// setting it here (after the import graph evaluated) let module-scope
// auto resources fire against the unconfigured bare fetcher.
app.use(resourcesPlugin)
app.use(translationsPlugin)

// frappe-ui's Button, Input and FormControl were registered globally here.
// Nothing rendered them any more (tests/audit/no-frappe-ui-controls bans
// them), and the registration was the trap GTag exists to dodge. Removed in
// alpha.12 C4: they kept feather-icons (157 KB) in every first download.
// EmptyState was registered here too until 8.11. It was the app's SECOND
// empty-state design — a bare centred sentence, or a thick dashed box for table
// fields — sitting beside GEmptyState's §10.1 #11 treatment, which is why one
// condition had three different looks across the app. Every consumer now uses
// GEmptyState and the component is deleted.
// ResourceError stays global for the original reason: it belongs on every screen
// that renders a resource, so requiring a per-file import is how it ends up on
// none of them.
app.component("ResourceError", ResourceError)

app.use(router)
app.use(IonicVue, getIonicConfig())

if (session?.isLoggedIn && !employeeResource?.data) {
	employeeResource.reload()
}

app.provide("$session", session)
app.provide("$user", userResource)
app.provide("$employee", employeeResource)
app.provide("$socket", socket)
app.provide("$dayjs", dayjs)

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

const registerServiceWorker = async () => {
	window.frappePushNotification = new FrappePushNotification("hrms")

	if ("serviceWorker" in navigator) {
		// At the app root, not /assets/hrms/frontend/: a worker controls only pages
		// under its own folder, so from there it never controlled /hrms and the
		// app had no offline launch (alpha.12 C1). hrms/www/service_worker.py.
		let serviceWorkerURL = "/hrms/sw.js"
		let config = ""

		if (window.frappe?.boot?.push_relay_server_url) {
			try {
				config = await window.frappePushNotification.fetchWebConfig()
				serviceWorkerURL = `${serviceWorkerURL}?config=${encodeURIComponent(
					JSON.stringify(config)
				)}`
			} catch (err) {
				console.error("Failed to fetch FCM config", err)
			}
		}

		navigator.serviceWorker
			.register(serviceWorkerURL, {
				type: "classic",
				scope: "/hrms",
			})
			.then((registration) => {
				if (config) {
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

router.isReady().then(async () => {
	if (import.meta.env.DEV) {
		await frappeRequest({
			url: "/api/method/hrms.www.hrms.get_context_for_dev",
		}).then(async (values) => {
			if (!window.frappe) window.frappe = {}
			window.frappe.boot = values
		})
	}

	await translationsPlugin.isReady()

	// index.html is static, so the tab title and the PWA install name were the
	// one place §16.6 could not reach. See utils/productName.js.
	applyProductName(app.config.globalProperties.__)

	registerServiceWorker()
	// Phones portrait, larger screens free (owner ruling; utils/orientationLock.js).
	lockPortraitOnPhones()
	app.mount("#app")
})

// Who may go where. The decision lives in router/navigationGate.js, where it
// is tested; only the server can end a session or reject an identity.
router.beforeEach(async (to) =>
	decideNavigation({ to, session, userResource, employeeResource, employeeGate })
)
