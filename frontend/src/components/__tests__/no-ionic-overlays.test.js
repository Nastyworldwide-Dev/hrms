// alpha.13 slice 4: two Ionic overlays each served ONE screen but loaded for
// everyone up front (measured: alert 45 KB, action-sheet 26 KB in the main
// bundle). The app has its own sheet and banner; these use them now.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../../", import.meta.url))
const files = (dir) =>
	readdirSync(dir).flatMap((n) => {
		const p = join(dir, n)
		if (statSync(p).isDirectory()) return n === "__tests__" ? [] : files(p)
		return /\.(vue|js)$/.test(n) ? [p] : []
	})

test("nothing uses Ionic's alert or action sheet", () => {
	const offenders = files(SRC)
		.filter((p) => /alertController|IonActionSheet|<ion-action-sheet|IonAlert\b/.test(readFileSync(p, "utf8")))
		.map((p) => p.slice(SRC.length))
	assert.deepEqual(offenders, [])
})

test("the workflow menu is the app's own action sheet", () => {
	const src = readFileSync(join(SRC, "components/WorkflowActionSheet.vue"), "utf8")
	assert.match(src, /<GActionSheet/)
})

// Firebase (~150 KB) was in every first download; push starts only after the
// app has drawn, only where a relay is configured. It loads on first use now.
test("firebase is loaded on first use, not in the first download", () => {
	const push = readFileSync(join(SRC, "utils/frappe-push-notification.js"), "utf8")
	assert.doesNotMatch(push, /^import .* from "firebase\//m)
	assert.match(push, /import\("firebase\/app"\)/)
	assert.match(push, /import\("firebase\/messaging"\)/)
})
