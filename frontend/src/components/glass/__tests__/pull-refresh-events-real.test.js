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

// 6 Oct 2026: this file pinned the SOURCE of the 28 Sep fix (a raw "ionRefresh" listener) and stayed green
// while a real pull on the running app still did nothing: the element fires "ion-refresh" (@ionic/vue's
// wrapper renames Ionic events to kebab-case). The behaviour is pinned by e2e/pull-refresh.spec.js, which
// drags with real touch events. These tests now pin that BOTH spellings are bound and cleaned up.
test("GPullRefresh binds both spellings of ionRefresh/ionStart by hand, not as a template directive", () => {
	const src = read("../GPullRefresh.vue")
	assert.doesNotMatch(template(src), /@ionRefresh=/)
	assert.doesNotMatch(template(src), /@ionStart=/)
	assert.match(src, /\[\["ion-start", "ionStart"\], onStart\]/)
	assert.match(src, /\[\["ion-refresh", "ionRefresh"\], onRefresh\]/)
	assert.match(src, /el\.addEventListener\(name, handler\)/)
	// cleaned up, not leaked across remounts
	assert.match(src, /el\.removeEventListener\(name, handler\)/)
	// one refresh per pull even if both spellings arrive
	assert.match(src, /SAME_PULL_MS/)
})

test("ListView binds both spellings of ionScroll by hand, not as a template directive", () => {
	const src = read("../../ListView.vue")
	assert.doesNotMatch(template(src), /@ionScroll=/)
	for (const name of ["ion-scroll", "ionScroll"]) {
		assert.match(src, new RegExp(`addEventListener\\("${name}", handleScroll\\)`))
		assert.match(src, new RegExp(`removeEventListener\\("${name}", handleScroll\\)`))
	}
})
