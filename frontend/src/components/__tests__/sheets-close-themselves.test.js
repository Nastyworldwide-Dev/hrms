// alpha.55 (owner report, 16 Oct 2026): a sheet that closed itself with
// modalController.dismiss() closed whichever overlay was on top: its own confirm,
// a dialog opened over it, or nothing while it was still animating. When it
// missed, the host kept the sheet "open" and the next one would not open. A
// sheet closes through the open state its host owns; only GModal (its own X and
// scrim) and the router's sheetGuard (closing sheets before a route lands) may
// dismiss an overlay directly.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../../", import.meta.url))
const files = (dir) =>
	readdirSync(dir).flatMap((n) => {
		const p = join(dir, n)
		if (statSync(p).isDirectory()) return n === "__tests__" ? [] : files(p)
		return /\.(vue|js)$/.test(n) ? [p] : []
	})

test("no sheet closes whichever overlay is on top", () => {
	const offenders = files(SRC)
		.map((p) => p.slice(SRC.length))
		.filter((p) => p !== "components/glass/GModal.vue")
		.filter((p) => /modalController\s*\.\s*dismiss\s*\(/.test(readFileSync(join(SRC, p), "utf8")))
	assert.deepEqual(offenders, [])
})

test("the check-in sheet and the list filters own their open state", () => {
	const checkin = readFileSync(join(SRC, "components/CheckInPanel.vue"), "utf8")
	assert.match(checkin, /:is-open="checkinSheetOpen"/)
	assert.doesNotMatch(checkin, /trigger="open-checkin-modal"/)
	const list = readFileSync(join(SRC, "components/ListView.vue"), "utf8")
	assert.match(list, /<GModal :is-open="filtersOpen"/)
	assert.doesNotMatch(list, /trigger="show-filter-modal"/)
})

// A failed transition used to throw out of the menu with the sheet left open
// and the host never told; now the menu closes and only success reaches the host.
test("the workflow menu closes before it acts, and a failure stays inside it", () => {
	const src = readFileSync(join(SRC, "components/WorkflowActionSheet.vue"), "utf8")
	const fn = src.slice(src.indexOf("const applyWorkflow = async"))
	assert.match(fn, /showActionSheet\.value = false\s*if \(!action\) return\s*try \{/)
	assert.match(fn, /emit\("workflow-applied"\)\s*\} catch/)
})
