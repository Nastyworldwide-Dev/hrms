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
import { vValueRow } from "@/utils/valueRow"
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
import { sessionEnded } from "@/utils/personalCache"
import getIonicConfig from "@/utils/ionicConfig"
import { employeeGate } from "@/utils/identity"

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
import { registerAppWorker } from "@/utils/serviceWorker"

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
// A label/value row puts a long value under its label, as iOS does (alpha.14 F).
app.directive("value-row", vValueRow)

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

	registerAppWorker()
	// Phones portrait, larger screens free (owner ruling; utils/orientationLock.js).
	lockPortraitOnPhones()
	app.mount("#app")
})

// Who may go where. The decision lives in router/navigationGate.js, where it
// is tested; only the server can end a session or reject an identity.
router.beforeEach(async (to) =>
	decideNavigation({ to, session, userResource, employeeResource, employeeGate, sessionEnded })
)
