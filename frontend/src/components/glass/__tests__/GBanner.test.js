// GBanner's interactive variant must be a keyboard-operable NATIVE <button>
// (WCAG 2.1.1). The tappable check-out and pending-approvals banners were
// <div role="status"> with an @click — mouse-only, unfocusable, wrong role.
//
// The node test runner here does not compile SFCs (see router/__tests__), so
// this pins the contract against the component source, the same way the router
// test asserts against its source. The runtime guarantee that GTag renders a
// real <button> and not frappe-ui's registered Button lives in GTag.test.js;
// here we prove GBanner routes through GTag and gets the roles right.
//
// Run with: node --test "frontend/**/*.test.js"
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../GBanner.vue", import.meta.url)), "utf8")

test("interactive routes through GTag to a native <button>, not <component :is>", () => {
	// <component :is="'button'"> resolves to frappe-ui's registered Button —
	// the GTag trap. GBanner must delegate the dynamic tag to GTag.
	assert.match(src, /import GTag from "\.\/GTag\.js"/, "must import GTag")
	assert.match(src, /<GTag/, "must render via GTag, not a bare element or <component :is>")
	assert.doesNotMatch(src, /<component\s+:is/, "must not use <component :is> for the tag (GTag trap)")
	assert.match(src, /:as="interactive \? 'button' : 'div'"/, "interactive -> button, else div")
	assert.match(src, /:type="interactive \? 'button' : undefined"/, "button must set type=button")
})

test("interactive emits click so keyboard activation reaches the parent", () => {
	assert.match(src, /@click="interactive && \$emit\('click', \$event\)"/, "must emit click when interactive")
	assert.match(src, /defineEmits\(\["click"\]\)/, "must declare the click emit")
})

test("passive banner keeps its live-region role; interactive drops it", () => {
	// a control is not a live region: role only on the passive <div>.
	assert.match(
		src,
		/:role="interactive \? undefined : variant === 'error' \? 'alert' : 'status'"/,
		"passive: error=alert, else status; interactive: no role (it is a button)",
	)
})
