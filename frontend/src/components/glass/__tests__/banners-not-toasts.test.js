// alpha.7 Phase 4 (plan §5.6): iOS says "done" / "that failed" with a banner
// that comes down from the TOP (a glass capsule), read out by VoiceOver.
// The app called frappe-ui's toast() directly in 50 places, each hand-picking
// an icon and a Tailwind colour (text-red-500, text-green-500...), all at the
// bottom, over the tab bar. One helper, gToast, now owns all of that.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../../../", import.meta.url))
const files = []
const walk = (d) => {
	for (const n of readdirSync(d)) {
		const p = join(d, n)
		if (n === "__tests__" || n === "node_modules") continue
		if (statSync(p).isDirectory()) walk(p)
		else if (/\.(vue|js)$/.test(n)) files.push(p)
	}
}
walk(SRC)

test("nothing calls frappe-ui's toast() except the one wrapper", () => {
	const offenders = files.filter((p) => {
		if (p.endsWith("glass/toast.js")) return false
		const s = readFileSync(p, "utf8")
		return /\btoast\(\{/.test(s) || /import \{[^}]*\btoast\b[^}]*\} from "frappe-ui"/.test(s)
	})
	assert.deepEqual(offenders.map((p) => p.slice(SRC.length)), [])
})

test("banners come down from the top", () => {
	const src = readFileSync(join(SRC, "components/glass/toast.js"), "utf8")
	assert.match(src, /position = "top-center"/)
})
