// The attendance data module's public surface.
//
// Written 23 September 2026 when `getShiftTiming` was removed: it existed for
// the Upcoming Shifts list on the Calendar screen, that list was deleted with
// the other three stacked sections (revamp §4), and the dead-code audit found
// it exported with no importer the moment the caller went.
//
// What is pinned is the seam itself — which helpers the rest of the app is
// allowed to depend on — because a data module accretes exports faster than
// anything else in a front end, and each one is a promise.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const source = readFileSync(join(SRC, "data/attendance.js"), "utf8")

const code = (text) =>
	text
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))

function walk(dir, out = []) {
	for (const entry of readdirSync(dir)) {
		const path = join(dir, entry)
		if (statSync(path).isDirectory()) {
			if (entry !== "__tests__") walk(path, out)
		} else if (/\.(vue|js)$/.test(entry)) out.push(path)
	}
	return out
}

test("every export has a caller", () => {
	// The dead-code audit checks this across the whole app; this checks it for
	// the module that just lost one, which is where the next orphan will be.
	const names = [...code(source).matchAll(/export const (\w+)/g)].map((m) => m[1])
	assert.ok(names.length > 0, "the module exports something")

	const users = walk(join(SRC, "components"))
		.concat(walk(join(SRC, "views")), walk(join(SRC, "data")))
		.filter((f) => !f.endsWith("data/attendance.js"))
		.map((f) => readFileSync(f, "utf8"))
		.join("\n")

	const orphans = names.filter((name) => !new RegExp(`\\b${name}\\b`).test(users))
	assert.deepEqual(orphans, [], "an export with no caller is a promise nobody asked for")
})

test("the helper the deleted list owned is gone", () => {
	// `getShiftTiming` formatted "09:00 - 18:00" for the Upcoming Shifts row.
	// That row went with the four stacked sections; the helper had no other
	// caller and no reason to survive them.
	assert.doesNotMatch(code(source), /getShiftTiming/)
})

test("the helpers the shift ROW still needs are kept", () => {
	// Deleting a list must not take the components that outlived it. Both of
	// these are called by ShiftAssignmentItem, which the shifts screen renders.
	for (const name of ["getShiftDates", "getTotalShiftDays"]) {
		assert.match(code(source), new RegExp(`export const ${name}`), `${name} still has a caller`)
	}
	const item = readFileSync(join(SRC, "components/ShiftAssignmentItem.vue"), "utf8")
	assert.match(item, /getShiftDates/)
	assert.match(item, /getTotalShiftDays/)
})
