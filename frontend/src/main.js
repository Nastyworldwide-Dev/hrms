// FIRST import, before anything that can declare an auto resource — see the
// comment inside; moving it below App.vue re-breaks the Team feature.
import "./resourceConfig"

import { createApp } from "vue"
import App from "./App.vue"
import router from "./router"
import { initSocket } from "./socket"

import { Button, Input, resourcesPlugin, FormControl } from "frappe-ui"
import { translationsPlugin } from "./plugins/translationsPlugin.js"
import EmptyState from "@/components/EmptyState.vue"
import ResourceError from "@/components/ResourceError.vue"

import { IonicVue } from "@ionic/vue"

import { session } from "@/data/session"
import { userResource } from "@/data/user"
import { employeeResource } from "@/data/employee"

import dayjs from "@/utils/dayjs"
import getIonicConfig from "@/utils/ionicConfig"

import FrappePushNotification from "../public/frappe-push-notification"

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

const app = createApp(App)
const socket = initSocket()

// The resourceFetcher config lives in ./resourceConfig, imported FIRST —
// setting it here (after the import graph evaluated) let module-scope
// auto resources fire against the unconfigured bare fetcher.
app.use(resourcesPlugin)
app.use(translationsPlugin)

app.component("Button", Button)
app.component("Input", Input)
app.component("FormControl", FormControl)
app.component("EmptyState", EmptyState)
// Registered globally beside EmptyState, for the same reason: it belongs on every
// screen that renders a resource, so requiring a per-file import is how it ends up
// on none of them.
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

const registerServiceWorker = async () => {
	window.frappePushNotification = new FrappePushNotification("hrms")

	if ("serviceWorker" in navigator) {
		let serviceWorkerURL = "/assets/hrms/frontend/sw.js"
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
			})
			.then((registration) => {
				if (config) {
					window.frappePushNotification.initialize(registration).then(() => {
						console.log("Frappe Push Notification initialized")
					})
				}
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
	registerServiceWorker()
	app.mount("#app")
})

router.beforeEach(async (to, _, next) => {
	let isLoggedIn = session.isLoggedIn

	try {
		if (isLoggedIn) await userResource.reload()
	} catch (error) {
		isLoggedIn = false
	}

	if (!isLoggedIn) {
		// password reset page is outside the PWA scope
		if (to.path === "/update-password") {
			return next(false)
		} else if (!["Login", "ForgotPassword"].includes(to.name)) {
			return next({ name: "Login" })
		}
	}

	if (isLoggedIn && to.name !== "InvalidEmployee") {
		await employeeResource.promise
		// user should be an employee to access the app
		// since all views are employee specific
		if (!employeeResource?.data || employeeResource?.data?.user_id !== userResource.data.name) {
			next({ name: "InvalidEmployee" })
		} else if (["Login", "ForgotPassword"].includes(to.name)) {
			next({ name: "Home" })
		} else {
			next()
		}
	} else {
		next()
	}
})
