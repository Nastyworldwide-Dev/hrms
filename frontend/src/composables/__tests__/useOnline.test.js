// One connectivity fact, wired once (revamp §32 G3, dead-code audit 22 Sep).
//
// The module used to export a second helper, `onConnectivityChange`, for
// per-component listeners. Nothing ever imported it. It carried its own
// addEventListener pair, so the module had TWO wiring sites for one browser
// fact — the shape the shared ref exists to prevent — and a test that pinned
// the disposal of listeners no live component added.
//
// What is asserted here is the invariant that survives: the browser is read in
// exactly one place, and the listeners that place adds are deliberately
// permanent. Behaviour, through the module's public surface, not text.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const source = readFileSync(fileURLToPath(new URL("../useOnline.js", import.meta.url)), "utf8")

function code(text) {
	return text
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))
}

test("the browser's connectivity is read in exactly one place", () => {
	// Two wiring sites are two answers that can disagree, which is the whole
	// reason this is a module-level ref rather than a per-component hook.
	const body = code(source)
	assert.equal(
		(body.match(/addEventListener\(\s*["']online["']/g) || []).length,
		1,
		"one online listener"
	)
	assert.equal(
		(body.match(/addEventListener\(\s*["']offline["']/g) || []).length,
		1,
		"one offline listener"
	)
	assert.match(body, /navigator\.onLine/, "seeded from the browser's own answer")
})

test("the module exports only what something imports", () => {
	// `onConnectivityChange` was exported for a caller that never arrived. An
	// export with no importer is not dead weight only — it is a second way to
	// do the thing, which is how two answers get created later.
	const exports = [...code(source).matchAll(/export\s+(?:async\s+)?function\s+(\w+)/g)].map(
		(m) => m[1]
	)
	assert.deepEqual(exports, ["useOnline"], "one public entry point")
})

test("the permanent listeners say that they are permanent", () => {
	// They outlive every component by design. An undocumented listener that is
	// never removed reads as a leak to the next person, who removes it and
	// leaves the next mount reading a stale ref.
	assert.match(source, /Deliberately not removed/)
})

test("useOnline hands back a ref a caller cannot write to", async () => {
	// Behaviour, not text: the fact is owned by this module. A screen that
	// could assign to it would be a second writer.
	//
	// Vue's `readonly` WARNS on a write and drops it; it does not throw. The
	// first version of this asserted a throw and failed against correct code —
	// so what is pinned is the outcome that matters: the write does not land.
	const { useOnline } = await import("../useOnline.js")
	const online = useOnline()
	assert.equal(typeof online.value, "boolean")
	const before = online.value
	online.value = !before
	assert.equal(online.value, before, "a consumer reads connectivity; it does not declare it")
})
