// Owner ruling (22 Sep): never an offline check-in. The check-in button was
// blocked offline in 6a3f0c968, but the two dialogs the same panel opens — a
// remote check-in and a late check-out — still sent their punch offline (review
// of that commit). Every check-in write the panel can reach is blocked offline,
// with the reason at the action. Source-asserted (no SFC compile in node).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

for (const name of ["RemoteCheckinDialog", "LateCheckoutDialog"]) {
	const src = readFileSync(fileURLToPath(new URL(`../${name}.vue`, import.meta.url)), "utf8")
	const template = src.slice(0, src.indexOf("<script"))

	test(`${name}: submit is disabled offline and says why`, () => {
		assert.match(src, /const online = useOnline\(\)/)
		assert.match(template, /:disabled="[^"]*!online[^"]*"/)
		assert.match(template, /__\("You need signal to check in\."\)/)
	})

	test(`${name}: submit refuses offline in code`, () => {
		const at = src.search(/(async function submit|const submit = async)/)
		assert.ok(at > 0, "submit exists")
		assert.match(src.slice(at, at + 400), /if \(!online\.value\)/)
	})
}
