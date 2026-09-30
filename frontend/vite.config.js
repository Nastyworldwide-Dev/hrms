import { readFileSync } from "node:fs"
import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import { VitePWA } from "vite-plugin-pwa"
import frappeui from "frappe-ui/vite"

import path from "path"
import fs from "fs"

//: @ionic/vue and @ionic/core ship no "sideEffects" flag, so Rollup keeps every
//: module @ionic/vue's index imports — ion-nav, ion-refresher, ion-back-button
//: and seventy more — in the first download, whether the app renders them or
//: not. Their component modules only define a class and register it when
//: defineCustomElement() is called (by the Vue wrapper, on first render), so
//: they are side-effect free. alpha.14 P1.
function ionicPure() {
	return {
		name: "nadi-ionic-side-effect-free",
		enforce: "pre",
		async resolveId(source, importer, options) {
			const r = await this.resolve(source, importer, { ...options, skipSelf: true })

			if (r && /node_modules\/@ionic\/(core\/components|vue\/dist)\//.test(r.id)) return { ...r, moduleSideEffects: false }
			return null
		},
		// `IonNav.name = "IonNav";` after each defineComponent is an assignment
		// Rollup cannot prove harmless, so every wrapper — and the component it
		// registers — stayed. The names are only read by Vue DevTools; nothing in
		// Ionic or this app looks a wrapper up by name.
		transform(code, id) {
			if (!id.includes("node_modules/@ionic/vue/dist/index.js")) return null
			const out = code.replace(/^(Ion[A-Za-z]+)\.name = ("Ion[A-Za-z]+");$/gm, "")
			return { code: out, map: null }
		},
	}
}

const PKG = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf8"))

export default defineConfig({
	// Stamped into the bundle so a report can say which build produced it —
	define: {
		// Which build a diagnostics report came from ("it worked yesterday"
		// needs yesterday to have a name). Reports only: never on screen
		// (owner, 27 Sep 2026: no date or time in the app).
		__APP_BUILD__: JSON.stringify(new Date().toISOString().slice(0, 16).replace("T", " ")),
		// The PWA's version (SemVer) and its release name, one source:
		// package.json. Shown on You; no build date or time (owner, 27 Sep
		// 2026). docs/glass/CHANGELOG.md has an entry per version, and
		// design/gates/version.test.mjs holds them together.
		__APP_VERSION__: JSON.stringify(PKG.version),
		__APP_RELEASE_NAME__: JSON.stringify(PKG.releaseName || ""),
	},
	server: {
		port: 8080,
		proxy: getProxyOptions(),
		allowedHosts: true,
	},
	plugins: [
		vue(),
		frappeui(),
		ionicPure(),
		VitePWA({
			// "prompt", not "autoUpdate": a new build used to activate and reload the
			// page the moment it downloaded — mid-session, mid-form, losing whatever
			// the employee had typed. It is still downloaded immediately; it takes
			// the page while the app is hidden (src/data/swRegistration.js).
			registerType: "prompt",
			strategies: "injectManifest",
			injectRegister: null,
			// main.js is the ONLY place the worker is registered (/hrms/sw.js,
			// served by hrms/www/service_worker.py, scope /hrms); swRegistration.js
			// watches that registration (src/data/swRegistration.js). Never add a
			// registerSW call: a second URL is a second worker, and the two swap
			// on every load (28 Sep 2026: the update bar showed with nothing new).
			buildBase: "/hrms/",
			scope: "/hrms",
			filename: "sw.js",
			devOptions: {
				enabled: true,
			},
			manifest: {
				display: "standalone",
				name: "Nadi",
				short_name: "Nadi",
				// Explicit id + scope: without them vite-plugin-pwa fills scope
				// from the Vite base (/assets/hrms/frontend/), which doesn't
				// contain start_url — Chrome then discards it and falls back to
				// scope "/", making the installed app capture the whole origin
				// and collide with other PWAs on the site (e.g. HandaPOS at /pos).
				id: "/hrms",
				scope: "/hrms",
				start_url: "/hrms",
				description: "Everyday HR & Payroll operations at your fingertips",
				// --g-bg dark. The manifest value paints the OS splash and the task
				// switcher BEFORE any JS runs, so a light literal here flashed white
				// on every dark launch — and the default theme mode is "system".
				// The in-browser chrome is not this value: data/theme.js reads --g-bg
				// after data-theme is set and writes it onto <meta name="theme-color">,
				// so that half already follows the token and must keep exactly one
				// such meta tag to query.
				theme_color: "#000000",
				icons: [
					{
						src: "/assets/hrms/manifest/manifest-icon-192.maskable.png",
						sizes: "192x192",
						type: "image/png",
						purpose: "any",
					},
					{
						src: "/assets/hrms/manifest/manifest-icon-192.maskable.png",
						sizes: "192x192",
						type: "image/png",
						purpose: "maskable",
					},
					{
						src: "/assets/hrms/manifest/manifest-icon-512.maskable.png",
						sizes: "512x512",
						type: "image/png",
						purpose: "any",
					},
					{
						src: "/assets/hrms/manifest/manifest-icon-512.maskable.png",
						sizes: "512x512",
						type: "image/png",
						purpose: "maskable",
					},
				],
			},
		}),
	],
	resolve: {
		alias: [
			// Only the frappe-ui parts this app uses (src/frappeUiLean.js). Exact
			// match: "frappe-ui/vite" and "frappe-ui/src/..." resolve as before.
			{ find: /^frappe-ui$/, replacement: path.resolve(__dirname, "src/frappeUiLean.js") },
			// The toast's icon component, with only the icons a toast draws
			// (src/toastIcons.js) instead of all of feather-icons (157 KB).
			{ find: /^\.\/FeatherIcon\.vue$/, replacement: path.resolve(__dirname, "src/toastIcons.js") },
			{ find: "@", replacement: path.resolve(__dirname, "src") },
		],
	},
	build: {
		outDir: "../hrms/public/frontend",
		emptyOutDir: true,
		// The floor is not es2015: this app requires backdrop-filter, service
		// workers and CSS custom properties, so no browser that can run it is
		// older than es2020. The old target transpiled async/await, spread and
		// optional chaining into helpers for browsers that could never load it.
		target: "es2020",
		commonjsOptions: {
			include: [/tailwind.config.js/, /node_modules/],
		},
		// `true` shipped 124 files and 12 MB of full source into
		// hrms/public/frontend/assets — served, and every one of them reachable.
		//
		// "hidden" was the first fix and is the wrong one HERE: it still writes
		// all 12 MB, it only stops the `//# sourceMappingURL` comment pointing at
		// them, and it is worth that trade only when something consumes the maps.
		// Nothing does — there is no error tracker configured anywhere in this
		// repo. Turn this back to "hidden" the day one is added, and upload the
		// maps to it rather than deploying them.
		sourcemap: false,
		rollupOptions: {
			output: {
				// frappe-ui as one forced chunk put its whole component set (rich
				// text editor, charts, calendar) in every first download: 900 KB of
				// JS before anything drew on a slow phone (alpha.12 C4, FCP 10.4 s).
				// Rollup now splits it by what each route actually imports.
			},
		},
	},
	optimizeDeps: {
		include: [
			"frappe-ui > feather-icons",
			"showdown",
			"tailwind.config.js",
			"engine.io-client",
		],
	},
})

function getProxyOptions() {
	const config = getCommonSiteConfig()
	const webserver_port = config ? config.webserver_port : 8000
	if (!config) {
		console.log("No common_site_config.json found, using default port 8000")
	}
	return {
		"^/(app|login|api|assets|files|private)": {
			target: `http://127.0.0.1:${webserver_port}`,
			ws: true,
			router: function (req) {
				const site_name = req.headers.host.split(":")[0]
				console.log(`Proxying ${req.url} to ${site_name}:${webserver_port}`)
				return `http://${site_name}:${webserver_port}`
			},
		},
	}
}

function getCommonSiteConfig() {
	let currentDir = path.resolve(".")
	// traverse up till we find frappe-bench with sites directory
	while (currentDir !== "/") {
		if (
			fs.existsSync(path.join(currentDir, "sites")) &&
			fs.existsSync(path.join(currentDir, "apps"))
		) {
			let configPath = path.join(currentDir, "sites", "common_site_config.json")
			if (fs.existsSync(configPath)) {
				return JSON.parse(fs.readFileSync(configPath))
			}
			return null
		}
		currentDir = path.resolve(currentDir, "..")
	}
	return null
}
