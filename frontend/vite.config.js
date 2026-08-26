import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import { VitePWA } from "vite-plugin-pwa"
import frappeui from "frappe-ui/vite"

import path from "path"
import fs from "fs"

export default defineConfig({
	server: {
		port: 8080,
		proxy: getProxyOptions(),
		allowedHosts: true,
	},
	plugins: [
		vue(),
		frappeui(),
		VitePWA({
			registerType: "autoUpdate",
			strategies: "injectManifest",
			injectRegister: null,
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
				theme_color: "#07070A",
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
		alias: {
			"@": path.resolve(__dirname, "src"),
		},
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
				manualChunks: {
					"frappe-ui": ["frappe-ui"],
				},
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
