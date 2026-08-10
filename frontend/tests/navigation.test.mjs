// Tests for the back-navigation fallback (v15.105.1). Opening a page cold
// (push-notification deep link) leaves no history entry, so router.back()
// silently strands the user; goBackOrHome must route Home instead.
import { test } from "node:test"
import assert from "node:assert/strict"

globalThis.window = globalThis.window || {}

const { goBackOrHome } = await import("../src/utils/navigation.js")

const mockRouter = () => {
	const calls = []
	return {
		calls,
		back: () => calls.push(["back"]),
		replace: (to) => calls.push(["replace", to]),
	}
}

test("goes back when a history entry exists", () => {
	globalThis.window.history = { state: { back: "/home" } }
	const router = mockRouter()
	goBackOrHome(router)
	assert.deepEqual(router.calls, [["back"]])
})

test("falls back to Home on a cold deep link (no back entry)", () => {
	globalThis.window.history = { state: { back: null } }
	const router = mockRouter()
	goBackOrHome(router)
	assert.deepEqual(router.calls, [["replace", { name: "Home" }]])
})

test("falls back to Home when history state is missing entirely", () => {
	globalThis.window.history = {}
	const router = mockRouter()
	goBackOrHome(router)
	assert.deepEqual(router.calls, [["replace", { name: "Home" }]])
})
