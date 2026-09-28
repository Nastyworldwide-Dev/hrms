// "The new update popup keeps appearing inappropriately" (owner, 28 Sep 2026).
//
// Two causes, both reproduced in a real browser on the dev site:
// 1. With push configured, main.js registers /hrms/sw.js?config=… while the
//    prompt's vite-plugin-pwa registerSW registered /hrms/sw.js. Same scope,
//    two URLs: each load installed the other as "waiting" — the bar showed on
//    4 of 4 loads with no deploy at all.
// 2. The dismissal was keyed on a __WB_REVISION__ in the worker's URL, which
//    has not existed since the worker moved to /hrms/sw.js (alpha.12), and was
//    read before anything was waiting — so nothing was remembered (dismissed
//    stayed null) and the bar returned on every reload.
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { test } from "node:test"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const code = (text) =>
	text
		.replace(/<!--[\s\S]*?-->/g, "")
		.replace(/\/\*[\s\S]*?\*\//g, "")
		.replace(/(^|[^:])\/\/[^\n]*/g, "$1")

const prompt = code(read("../UpdatePrompt.vue"))
const main = code(read("../../main.js"))
const sw = code(read("../../../public/sw.js"))

test("the prompt registers no service worker of its own", () => {
	assert.doesNotMatch(
		prompt,
		/virtual:pwa-register|registerSW\(/,
		"one worker, registered once, by main.js"
	)
	assert.doesNotMatch(prompt, /serviceWorker\.register\(/)
})

test("main.js hands its one registration to the prompt", () => {
	assert.match(
		main,
		/serviceWorker[\s\S]*?\.register\(serviceWorkerURL/,
		"main.js still registers it"
	)
	assert.match(main, /setRegistration\(registration\)/, "and shares the registration")
})

test("the prompt asks the waiting build for its own id before offering it", () => {
	assert.match(prompt, /GET_BUILD_ID/)
	assert.match(prompt, /shouldOfferUpdate\(id, remembered\(\)\)/, "the answer decides the offer")
})

test("the worker answers with the id of what it precaches", () => {
	assert.match(sw, /buildIdOf\(/)
	assert.match(sw, /"GET_BUILD_ID"/)
})

test("a first install is not an update", () => {
	// Only a worker waiting behind an ACTIVE one is a new version; the very
	// first install has nothing to replace.
	assert.match(prompt, /registration\.active/)
})
