// alpha.7 §5.7: while the selfie camera is open the screen stays on (Screen
// Wake Lock; iOS 18.4+). Released when the camera stops; silent where missing.
import { test } from "node:test"
import assert from "node:assert/strict"
import { holdScreen, releaseScreen } from "../wakeLock.js"

test("held while the camera is open, released after", async () => {
	const log = []
	const nav = {
		wakeLock: {
			request: async (type) => {
				log.push(["request", type])
				return { release: async () => log.push(["release"]) }
			},
		},
	}
	await holdScreen(nav)
	await releaseScreen()
	await releaseScreen()
	assert.deepEqual(log, [["request", "screen"], ["release"]])
})

test("missing or refused is silent", async () => {
	await holdScreen({})
	await holdScreen({ wakeLock: { request: () => Promise.reject(new Error("denied")) } })
	await releaseScreen()
})
