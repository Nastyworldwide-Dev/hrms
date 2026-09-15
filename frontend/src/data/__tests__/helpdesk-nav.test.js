// Helpdesk is native now (v16.23.0): it must be a router destination inside
// the PWA, never an Apps link-out. Since 15 Sep 2026 it shares ONE page with
// HR Issues (views/helpdesk/HelpdeskHub.vue): the sidebar entry is ungated —
// HR Issues is for everyone — and the availability gate moved onto the IT pill.
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

test("navItems has one ungated Helpdesk entry and the IT pill carries the availability gate", () => {
	const nav = read("../navItems.js")
	assert.match(nav, /title: "Helpdesk",[\s\S]*?route: HUB_PATH/)
	assert.ok(!nav.includes("HELPDESK_ITEM"), "no separate gated entry any more")
	for (const file of ["../../views/More.vue", "../../components/SideNav.vue"]) {
		const src = read(file)
		assert.ok(!/helpdeskAvailable/.test(src), `${file} must not gate the Helpdesk entry`)
	}
	const hub = read("../../views/helpdesk/HelpdeskHub.vue")
	assert.match(hub, /helpdeskAvailable\.data/, "the hub gates the IT pill on helpdeskAvailable")
})
