// HR policy (owner, 23 Sep 2026): "anything related to banked overtime is
// removed... we dont use banked overtime." The PWA offers no bank, no
// hours -> leave converter and no replacement-leave claim form. Old addresses
// land on Requests so a saved link never 404s.
// Run: cd frontend && node --test tests/no-banked-overtime.test.mjs
import test from "node:test"
import assert from "node:assert/strict"
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../src", import.meta.url))
const walk = (dir) =>
	readdirSync(dir).flatMap((name) => {
		const path = join(dir, name)
		if (statSync(path).isDirectory())
			return name === "__tests__" ? [] : walk(path)
		return /\.(vue|js)$/.test(name) ? [path] : []
	})

test("the bank screens are gone", () => {
	for (const file of [
		"components/ReplacementLeaveCard.vue",
		"views/ot/ReplacementLeave.vue",
		"views/ot/ReplacementLeaveClaimForm.vue",
	]) {
		assert.ok(!existsSync(join(SRC, file)), `${file} still exists`)
	}
})

test("nothing links to them", () => {
	const offenders = walk(SRC).filter((file) =>
		/ReplacementLeaveView|ReplacementLeaveClaimFormView|ReplacementLeaveCard/.test(
			readFileSync(file, "utf8")
		)
	)
	assert.deepEqual(offenders, [])
})

test("an old address lands on Requests", () => {
	const routes = readFileSync(join(SRC, "router/ot.js"), "utf8")
	assert.match(
		routes,
		/path: "\/replacement-leave\/:rest\(\.\*\)\*",\s*redirect: "\/requests"/
	)
})
