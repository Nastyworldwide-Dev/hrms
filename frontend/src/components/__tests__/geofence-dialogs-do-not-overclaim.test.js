// A distance figure drawn from a coarse reading is an accusation the data
// cannot support — and the reason code no longer says which readings those are.
//
// Both dialogs used to hide the precise distance for `imprecise_location` only,
// which was a fair proxy while that reason covered every coarse reading. Since
// 17 Sep 2026 a reading between 250 m and 2000 m of error is trusted enough to
// be placed, so a genuinely-far one comes back as `outside_radius` — and would
// have rendered "+820 m over" with no accuracy caveat at all, for a reading the
// geofence itself calls too coarse to widen a fence with. Their own comments
// warn against exactly that: "telling someone they left the geofence when their
// phone simply could not see the sky" is "the kind of wrong that gets argued
// about at payroll".
//
// Source-asserted: the node runner does not compile SFCs.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (name) =>
	readFileSync(fileURLToPath(new URL(`../${name}`, import.meta.url)), "utf8")

const DIALOGS = ["StrictRejectionDialog.vue", "RemoteCheckinDialog.vue"]

for (const name of DIALOGS) {
	test(`${name} decides on the accuracy, not on the reason string alone`, () => {
		const src = read(name)
		assert.match(
			src,
			/readingIsCoarse/,
			"the precise figure must be gated on how coarse the reading was"
		)
		assert.match(
			src,
			/isReadingCoarse/,
			"and through the shared test, not a retyped comparison against 250"
		)
	})

	test(`${name} can say how coarse the reading was`, () => {
		const src = read(name)
		assert.match(src, /accuracyM/, "it needs the accuracy to say anything honest about it")
	})
}

// A hidden number and a confident sentence above it is still an overclaim.
for (const name of DIALOGS) {
	test(`${name} does not assert the verdict in words either`, () => {
		const src = read(name)
		// Every branch that decides WORDING from the reason must also ask how
		// coarse the reading was — otherwise the card says "we cannot place you"
		// while the headline right above it says "you are outside the geofence".
		const wording = [...src.matchAll(/const (?:title|subtitle|headline) = computed\(/g)]
		assert.ok(wording.length, "the dialog decides some wording")
		for (const match of wording) {
			const block = src.slice(match.index, src.indexOf("\n})", match.index))
			assert.match(
				block,
				/readingIsCoarse/,
				"wording branched on the reason string alone, one line above a card that knows better"
			)
		}
	})
}

test("the coarse-reading test is written once, not copied into each surface", () => {
	// Three hand-copies of `accuracy > 250` across two dialogs and the sheet is
	// the exact shape that let the reason-string check drift out of step twice
	// in one day.
	const shared = readFileSync(
		fileURLToPath(new URL("../../utils/geolocation.js", import.meta.url)),
		"utf8"
	)
	assert.match(shared, /export function isReadingCoarse/, "one definition, exported")
	for (const name of [...DIALOGS, "CheckInPanel.vue"]) {
		const src = read(name)
		assert.match(src, /isReadingCoarse/, `${name} must use the shared test`)
		assert.doesNotMatch(
			src,
			/>\s*ACCURACY_ALLOWANCE_CAP_M/,
			`${name} must not re-derive the comparison`
		)
	}
})
