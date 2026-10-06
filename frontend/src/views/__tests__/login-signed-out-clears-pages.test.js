// AU-5 (alpha.36): a session that ends on its own never passes through Log out, so the offline copy of
// the /hrms page (cache "nadi-pages", rendered per user) stayed on the phone for the next person.
// Login is where such a session lands, and it knows it did: takeSignedOutNotice() is true. That one
// branch must clear the copy; a plain visit to Login must not touch it.
// Compiles the real Login.vue setup (HelpdeskHub.test.js recipe); the notice, the cache clearer, the
// resources and injection are the boundaries.
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
	const cleared = []
	const bindings = {
		reactive,
		ref,
		inject: () => (text) => text,
		createResource: () => ({ data: null }),
		takeSignedOutNotice: () => signedOut,
		clearCachedPages: () => {
			cleared.push(1)
			return new Promise(() => {}) // never settles: the page must not wait for it
		},
		console: { info() {}, warn() {}, error() {} },
	}
	for (const name of Object.keys(script.imports)) if (!(name in bindings)) bindings[name] = {}
	const component = new Function(...Object.keys(bindings), code)(...Object.values(bindings))
	const vm = component.setup({}, { expose() {} })
	return { vm, cleared }
}

test("a session that ended on its own: the banner shows and the saved pages are cleared once", () => {
	const { vm, cleared } = visit({ signedOut: true })
	assert.equal(vm.signedOut, true)
	assert.equal(cleared.length, 1)
})

test("a plain visit to Login leaves the saved pages alone", () => {
	const { vm, cleared } = visit({ signedOut: false })
	assert.equal(vm.signedOut, false)
	assert.equal(cleared.length, 0)
})

test("clearing never blocks the page: setup stays synchronous", () => {
	// a top-level await would make the whole Login an async component (Suspense) and hold the form
	// back until Cache Storage answered
	assert.doesNotMatch(code, /\bawait clearCachedPages/)
	assert.match(source, /import \{ clearCachedPages \} from "@\/utils\/cachedPages"/)
})
