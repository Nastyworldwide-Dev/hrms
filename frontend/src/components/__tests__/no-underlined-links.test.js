// alpha.6 C5: section links ("View list", "View leave history", "All
// check-ins") were underlined web links, 15px tall. iOS writes a section
// action as a plain tinted text button ("See All" in Apple's own apps; HIG
// Buttons: plain style), and a destination the person navigates to as a list
// row with a chevron (HIG Lists and tables). No underlined links in the app.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const vues = []
const walk = (dir) => {
	for (const name of readdirSync(dir)) {
		const p = join(dir, name)
		if (name === "__tests__" || name === "node_modules") continue
		if (statSync(p).isDirectory()) walk(p)
		else if (p.endsWith(".vue")) vues.push(p)
	}
}
walk(SRC)

test("no link in the app is drawn underlined", () => {
	const offenders = vues.filter((p) => /class="[^"]*\bunderline underline-offset-link\b/.test(readFileSync(p, "utf8")))
	assert.deepEqual(offenders.map((p) => p.replace(SRC, "")), [])
})

test("Calendar's two destinations are list rows with a chevron", () => {
	const cal = readFileSync(join(SRC, "views/attendance/Dashboard.vue"), "utf8")
	assert.match(cal, /<GListRow[^>]*All check-ins|All check-ins[\s\S]{0,200}<\/GListRow>|:label="__\('All check-ins'\)"/)
	assert.match(cal, /:label="__\('Your shifts'\)"/)
})
