// R1 (alpha.37): clearing the offline page copy of a session that ended on its own moved out of Login
// (alpha.36 AU-5) into sessionEnded() in utils/personalCache.js, which runs BEFORE the reload onto
// Login (tested in utils/__tests__/sessionEnded.test.js). Login keeps only the banner: it reads the
// one-shot notice once, and no longer touches Cache Storage itself.
// Compiles the real Login.vue setup (HelpdeskHub.test.js recipe).
import assert from "node:assert/strict"
import { test } from "node:test"
import { readFileSync } from "node:fs"
import { compileScript, parse } from "@vue/compiler-sfc"
import { reactive, ref } from "vue"

const source = readFileSync(new URL("../Login.vue", import.meta.url), "utf8")
const script = compileScript(parse(source).descriptor, { id: "login" })
const code = script.content
	.replace(/import[\s\S]*?from ["'][^"']+["'];?/g, "")
	.replace("export default", "return")

function visit({ signedOut }) {
	let reads = 0
	const bindings = {
		reactive,
		ref,
		inject: () => (text) => text,
		createResource: () => ({ data: null }),
		takeSignedOutNotice: () => (reads++, signedOut),
		console: { info() {}, warn() {}, error() {} },
	}
	for (const name of Object.keys(script.imports)) if (!(name in bindings)) bindings[name] = {}
	const component = new Function(...Object.keys(bindings), code)(...Object.values(bindings))
	const vm = component.setup({}, { expose() {} })
	return { vm, reads: () => reads }
}

test("a session that ended on its own: the banner shows, the notice is read once", () => {
	const { vm, reads } = visit({ signedOut: true })
	assert.equal(vm.signedOut, true)
	assert.equal(reads(), 1)
})

test("a plain visit to Login shows no banner", () => {
	assert.equal(visit({ signedOut: false }).vm.signedOut, false)
})

test("Login no longer clears the offline page copy: sessionEnded() did, before the reload", () => {
	assert.doesNotMatch(source, /cachedPages|clearCachedPages/)
})
