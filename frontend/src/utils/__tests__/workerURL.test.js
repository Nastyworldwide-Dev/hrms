// The update bar still came back on real phones after alpha.16 (owner, 28 Sep
// 2026). Reproduced on the dev site: the SAME build registered under a
// different address (/hrms/sw.js?config=A, then ?config=B, then no config)
// counts as a new worker every time, and the bar offers it on every launch.
// Live, the address carries the push settings fetched from the relay on each
// launch; a slow or failed fetch registered the plain address, the next
// launch the full one. The address must come out the same for the same
// settings, and a failed fetch must reuse the last good settings.
import assert from "node:assert/strict"
import { test } from "node:test"

import { workerURL } from "../workerURL.js"

const BASE = "/hrms/sw.js"
const cfg = { apiKey: "k", projectId: "p", messagingSenderId: "1", appId: "a" }

test("the same settings in a different order give the same address", () => {
	const shuffled = { appId: "a", messagingSenderId: "1", projectId: "p", apiKey: "k" }
	assert.equal(workerURL(BASE, cfg, null), workerURL(BASE, shuffled, null))
})

test("nested settings are ordered too", () => {
	const a = { x: { b: 1, a: 2 }, y: 1 }
	const b = { y: 1, x: { a: 2, b: 1 } }
	assert.equal(workerURL(BASE, a, null), workerURL(BASE, b, null))
})

test("a failed fetch reuses the last good settings, not the plain address", () => {
	const good = workerURL(BASE, cfg, null)
	assert.equal(workerURL(BASE, null, cfg), good)
})

test("never fetched and none stored: the plain address", () => {
	assert.equal(workerURL(BASE, null, null), BASE)
})

test("fresh settings win over stored ones", () => {
	const fresh = { ...cfg, appId: "b" }
	assert.equal(workerURL(BASE, fresh, cfg), workerURL(BASE, fresh, null))
	assert.notEqual(workerURL(BASE, fresh, null), workerURL(BASE, cfg, null))
})

test("the worker can still read the settings back", () => {
	const url = new URL(workerURL(BASE, cfg, null), "https://x.example")
	assert.deepEqual(JSON.parse(url.searchParams.get("config")), cfg)
})
