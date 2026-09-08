// Helpdesk is native now (v16.23.0): it must be a router destination inside
// the PWA, never an Apps link-out, and it must hide on sites without the app.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { APP_LINKS } from "../appLinks.js"

const read = (rel) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8")

test("helpdesk is no longer an app link-out", () => {
	assert.ok(!APP_LINKS.some((l) => l.key === "helpdesk"))
	assert.ok(!APP_LINKS.some((l) => l.href.startsWith("/helpdesk")))
})

test("navItems declares a Helpdesk route and More/SideNav gate it on availability", () => {
	const nav = read("../navItems.js")
	assert.match(nav, /HELPDESK_ITEM[\s\S]*route: "\/helpdesk"/)
	for (const file of ["../../views/More.vue", "../../components/SideNav.vue"]) {
		const src = read(file)
		assert.match(src, /helpdeskAvailable\.data/, `${file} must gate Helpdesk on helpdeskAvailable`)
	}
})
