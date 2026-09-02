// FormView renders its entire UI — header, Back button and all — inside
// `v-if="isFormReady"`. A slow or failed document fetch (404, no permission,
// dropped network) leaves isFormReady false forever, so without a v-else the
// screen is blank with no spinner, no error and no way back — on every one of
// the six request detail/edit views. This pins the recovery branch so it
// cannot silently regress. Source-asserted because the node runner does not
// compile SFCs (see router/__tests__).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../FormView.vue", import.meta.url)), "utf8")

test("a failed/slow document load has a recovery branch, not a blank screen", () => {
	// the happy UI is gated on isFormReady...
	assert.match(src, /v-if="isFormReady"/, "form UI is gated on isFormReady")
	// ...so there MUST be a sibling v-else that renders something.
	assert.match(src, /<div v-else class="flex flex-col h-full w-full form-view-root">/, "must have a v-else recovery branch")
})

test("the recovery branch gives the user a way out (Back + Try again)", () => {
	// find the v-else block and assert it carries an escape hatch.
	const elseIdx = src.indexOf("<div v-else")
	assert.ok(elseIdx > 0, "v-else branch exists")
	const tail = src.slice(elseIdx)
	assert.match(tail, /goBackOrHome\(router\)/, "recovery branch must keep a Back action")
	assert.match(tail, /reloadDoc\(\)/, "recovery branch must offer Try again / retry")
	assert.match(tail, /documentResource\.get\.loading/, "recovery branch distinguishes loading from error")
})
