// 28 Sep 2026 (owner report: pull-to-refresh never actually reloaded
// anything, list pages never loaded more on scroll). Vue's runtime-dom
// hyphenates a template `@ionRefresh=`/`@ionScroll=` binding down to a
// listener for "ion-refresh"/"ion-scroll" (parseName: hyphenate(name.slice(2)))
// before it ever reaches the DOM. Ionic's real components dispatch these with
// the exact camelCase name they were authored with (createEvent(this,
// "ionRefresh", …) in @ionic/core) — the two names never meet, so the
// template-directive form is silently inert. Confirmed live: intercepting
// every addEventListener call on a running page showed "ion-refresh"
// registered while the element only ever dispatches "ionRefresh".
//
// The fix is a raw addEventListener with the literal name, from a template
// ref. This test pins the SOURCE shape so the inert form cannot come back.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

const template = (src) => src.slice(src.indexOf("<template>"), src.indexOf("</template>"))

test("GPullRefresh binds ionRefresh/ionStart by hand, not as a template directive", () => {
	const src = read("../GPullRefresh.vue")
	assert.doesNotMatch(template(src), /@ionRefresh=/)
	assert.doesNotMatch(template(src), /@ionStart=/)
	assert.match(src, /addEventListener\("ionStart", onStart\)/)
	assert.match(src, /addEventListener\("ionRefresh", onRefresh\)/)
	// cleaned up, not leaked across remounts
	assert.match(src, /removeEventListener\("ionStart", onStart\)/)
	assert.match(src, /removeEventListener\("ionRefresh", onRefresh\)/)
})

test("ListView binds ionScroll by hand, not as a template directive", () => {
	const src = read("../../ListView.vue")
	assert.doesNotMatch(template(src), /@ionScroll=/)
	assert.match(src, /addEventListener\("ionScroll", handleScroll\)/)
	assert.match(src, /removeEventListener\("ionScroll", handleScroll\)/)
})
