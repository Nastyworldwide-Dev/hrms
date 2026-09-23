// "A new version is ready" → Reload did nothing on a real phone, and the bar
// kept coming back (owner, 23 Sep). The library reloads only when the browser
// reports the new worker took control; when that event never arrives, the tap
// is lost. Reload must always end in a reload.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const source = readFileSync(fileURLToPath(new URL("../UpdatePrompt.vue", import.meta.url)), "utf8")
const reloadFn = source.slice(source.indexOf("function reload()"))

test("Reload tells the waiting build to take over directly", () => {
	assert.match(reloadFn, /swRegistration\?\.waiting\?\.postMessage\(\{ type: "SKIP_WAITING" \}\)/)
})

test("Reload reloads when the new build takes control", () => {
	assert.match(reloadFn, /addEventListener\("controllerchange"/)
})

test("Reload reloads anyway if the browser never says so", () => {
	assert.match(reloadFn, /setTimeout\([\s\S]*?once\(\)[\s\S]*?RELOAD_FALLBACK_MS\)/)
	assert.match(reloadFn, /const once = \(\) => \{[\s\S]*?window\.location\.reload\(\)/)
})

test("the bar goes away as soon as Reload is tapped", () => {
	assert.match(reloadFn, /needRefresh\.value = false/)
})

test("a build that never takes over is not offered again and again", () => {
	// Review of 1526e13bb: the fallback reload landed on the same waiting build,
	// with the dismissal just cleared, so the bar came straight back.
	assert.match(reloadFn, /remember\(waitingId\)\s*\n\s*once\(\)/)
})

test("a double tap reloads once", () => {
	assert.match(source, /if \(reloading\) return\s*\n\s*reloading = true/)
})
