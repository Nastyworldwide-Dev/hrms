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
			/ACCURACY_ALLOWANCE_CAP_M/,
			"and on the same cap the geofence uses, not a retyped number"
		)
	})

	test(`${name} can say how coarse the reading was`, () => {
		const src = read(name)
		assert.match(src, /accuracyM/, "it needs the accuracy to say anything honest about it")
	})
}
