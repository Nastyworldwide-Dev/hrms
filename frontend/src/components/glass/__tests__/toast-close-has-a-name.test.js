// axe button-name (critical) + target-size, on every screen that shows a toast:
// frappe-ui's Toast close button is an icon in a 20x20 box with no name. It is
// vendor code, so the fix lives in patches/frappe-ui+0.1.105.patch (applied by
// the postinstall patch-package run); this test reads the INSTALLED file, so a
// reinstall that drops the patch, or a frappe-ui bump that moves the button,
// goes red here instead of silently in production.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const toast = readFileSync(
	fileURLToPath(new URL("../../../../node_modules/frappe-ui/src/components/Toast.vue", import.meta.url)),
	"utf8"
)
const close = toast.match(/<button\b[\s\S]*?@click="\$emit\('close'\)"[\s\S]*?>/)?.[0] ?? ""

test("the toast close button has a name a screen reader says", () => {
	assert.ok(close, "Toast.vue still has its close button")
	assert.match(close, /aria-label="Close"/)
})

test("its tap area is at least 44 px while the X stays the same size", () => {
	assert.match(close, /min-h-11\b/)
	assert.match(close, /min-w-11\b/)
	assert.match(toast, /<FeatherIcon name="x" class="h-4 w-4/)
})

test("the patch file carries the change, so a fresh install gets it", () => {
	const patch = readFileSync(fileURLToPath(new URL("../../../../patches/frappe-ui+0.1.105.patch", import.meta.url)), "utf8")
	assert.match(patch, /\+\+\+ b\/node_modules\/frappe-ui\/src\/components\/Toast\.vue/)
	assert.match(patch, /\+\s+aria-label="Close"/)
})
