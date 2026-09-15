// The KPI page threw during setup — "Cannot access 'teamData' before
// initialization" — so it never mounted its <ion-page>. Ionic's outlet kept a
// view item with no element, and every later enter/leave errored
// ("Cannot read properties of undefined (reading 'classList')",
// "instance.update is not a function"): Home -> KPI -> back looked stuck.
//
// The cause is ORDER inside <script setup>: `watch(() => teamData.value, …)`
// runs its getter synchronously at creation to collect dependencies, and
// `const teamData = computed(…)` sat twenty lines further down, still in the
// temporal dead zone. Source-asserted because the node runner does not compile
// SFCs (see router/__tests__). Run with: cd frontend && node --test
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const sfc = readFileSync(fileURLToPath(new URL("../Dashboard.vue", import.meta.url)), "utf8")
// Comments stripped: the page's own comments quote `watch(() => teamData.value)`
// when explaining this very ordering, and prose is not a read.
const script = sfc
	.slice(sfc.indexOf("<script setup>"), sfc.indexOf("</script>"))
	.replace(/\/\*[\s\S]*?\*\//g, "")
	.replace(/^\s*\/\/.*$/gm, "")

// Every `watch(...)` whose source is an identifier or `() => ident.value` reads
// that identifier the moment the watch is created, not when it first fires.
function watchedIdentifiers(src) {
	const out = []
	const re = /\bwatch\(\s*(?:\(\)\s*=>\s*)?([A-Za-z_$][\w$]*)/g
	for (let m; (m = re.exec(src)); ) out.push({ name: m[1], at: m.index })
	return out
}

function declaredAt(src, name) {
	const m = new RegExp(`\\b(?:const|let|var|function)\\s+${name}\\b`).exec(src)
	return m ? m.index : -1
}

test("teamData is declared before the watch that reads it at setup", () => {
	const watched = watchedIdentifiers(script).find((w) => w.name === "teamData")
	assert.ok(watched, "the page watches teamData")
	const decl = declaredAt(script, "teamData")
	assert.ok(decl !== -1, "teamData is declared in <script setup>")
	assert.ok(
		decl < watched.at,
		"const teamData must come before watch(() => teamData.value): the getter runs at setup"
	)
})

test("no watch source in the KPI page is read before its declaration (invariant)", () => {
	for (const { name, at } of watchedIdentifiers(script)) {
		const decl = declaredAt(script, name)
		if (decl === -1) continue // imported (refs from @/data) — never in the TDZ
		assert.ok(decl < at, `watch reads '${name}' at setup but it is declared later (TDZ)`)
	}
})
