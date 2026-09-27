// alpha.14 (states audit, 27 Sep 2026): with every server read failing, You
// (and /settings, which redirects to it) hung on the launch placeholder 1 run
// in 3–4. The navigation gate lets a person through when their employee
// record has not been read yet (offline, or the read failed: navigationGate
// "employee unknown"), but Profile built its document resource from
// `employee.data.name` while the page was being set up — null, a TypeError,
// and the page never mounted. It must build without an employee and show
// "Could not load your details" with Try again.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../Profile.vue", import.meta.url)), "utf8")
const script = src.slice(src.indexOf("<script setup>"))

test("You never reads employee.data.name while the page is set up", () => {
	// only inside functions/handlers, guarded; never at the top level of setup
	const topLevel = script.split("\n").filter((l) => /^(const|let|\t\w+:)/.test(l) || /^\tname: /.test(l))
	assert.ok(!topLevel.some((l) => /employee\.data\.name/.test(l)), topLevel.filter((l) => /employee\.data\.name/.test(l)).join("\n"))
	assert.match(script, /name: employee\.data\?\.name/)
})

// The same class on the form and list pages (alpha.14): a read of
// employee.data.<field> while the page is set up threw when the employee had
// not been read. Inside functions that run later it is fine; at setup it is not.
test("no view reads employee.data.<field> at setup without ?.", async () => {
	const { readdirSync, statSync } = await import("node:fs")
	const root = fileURLToPath(new URL("..", import.meta.url))
	const walk = (d) => readdirSync(d).flatMap((n) => { const p = `${d}/${n}`; return statSync(p).isDirectory() ? (n === "__tests__" ? [] : walk(p)) : p.endsWith(".vue") ? [p] : [] })
	const bad = []
	for (const file of walk(root)) {
		const script = readFileSync(file, "utf8").split("<script setup>")[1] || ""
		for (const line of script.split("\n")) {
			// top-level statements and object properties of top-level calls: one tab or none
			if (!/^(const |let |\t[a-z_]+: )/.test(line)) continue
			if (/(employee|sessionEmployee)\.data\.[a-z_]+/.test(line)) bad.push(`${file.split("/views/")[1]}: ${line.trim()}`)
		}
	}
	assert.deepEqual(bad, [])
})
