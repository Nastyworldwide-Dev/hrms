// Team scrolled 34 px with nothing below (audit P2-2). ion-content inside the
// tab shell already reserves the tab bar's height (glass-components.css,
// tabbar-reservation.test.mjs); a page that adds pb-24 on top reserves it
// twice, and a short page scrolls for nothing.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

for (const file of ["../More.vue", "../team/TeamDashboard.vue", "../team/TeamRoster.vue", "../sop/SopList.vue"]) {
	test(`${file} does not reserve the tab bar a second time`, () => {
		const src = readFileSync(fileURLToPath(new URL(file, import.meta.url)), "utf8")
		assert.doesNotMatch(src, /\bpb-24\b/)
	})
}
