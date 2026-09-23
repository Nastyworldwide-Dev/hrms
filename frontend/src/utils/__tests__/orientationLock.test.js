// Owner ruling (22 Sep): phones are portrait-locked; tablets and desktop adapt.
// The manifest's `orientation` cannot express that — it locks the installed
// app on every device, tablets included — so the lock is asked for at runtime,
// only on a phone-sized screen, only when installed (audit F-3, APP-15).
// iOS offers no web API to lock orientation; there the request is skipped.
import { test } from "node:test"
import assert from "node:assert/strict"

import { shouldLockPortrait, lockPortraitOnPhones } from "../orientationLock.js"

const env = (over = {}) => ({
	shortSide: 390,
	standalone: true,
	canLock: true,
	...over,
})

test("an installed phone locks to portrait", () => {
	assert.equal(shouldLockPortrait(env()), true)
})

test("a tablet or desktop is left to adapt", () => {
	assert.equal(shouldLockPortrait(env({ shortSide: 768 })), false)
	assert.equal(shouldLockPortrait(env({ shortSide: 1024 })), false)
})

test("in a browser tab (not installed) nothing is locked", () => {
	assert.equal(shouldLockPortrait(env({ standalone: false })), false)
})

test("where the platform cannot lock (iOS), nothing is asked", () => {
	assert.equal(shouldLockPortrait(env({ canLock: false })), false)
})

test("a refused lock never throws", async () => {
	const orientation = { lock: () => Promise.reject(new Error("NotSupportedError")) }
	await lockPortraitOnPhones({ ...env(), orientation })
})

test("an allowed lock asks for portrait", async () => {
	let asked = null
	const orientation = { lock: (mode) => ((asked = mode), Promise.resolve()) }
	await lockPortraitOnPhones({ ...env(), orientation })
	assert.equal(asked, "portrait")
})

test("the app asks for the lock at start-up", async () => {
	const { readFileSync } = await import("node:fs")
	const main = readFileSync(new URL("../../main.js", import.meta.url), "utf8")
	assert.match(main, /lockPortraitOnPhones\(\)/)
})
