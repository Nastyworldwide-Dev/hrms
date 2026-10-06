// A screen reader opening any sheet heard "dialog" and nothing else (axe
// aria-dialog-name, serious). Ionic draws its OWN role=dialog wrapper inside
// ion-modal and names it only from an aria-label on the ion-modal host
// (@ionic/core 7.4 modal: inheritAttributes(el, ['aria-label', 'role'])); the
// label on our inner .g-sheet never reached it. One attribute on the host
// names every GModal sheet in the app.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../GModal.vue", import.meta.url)), "utf8")
const host = src.match(/<ion-modal\b[^>]*>/)?.[0] ?? ""

test("the ion-modal host carries the sheet's title as its accessible name", () => {
	assert.ok(host, "GModal renders an ion-modal")
	assert.match(host, /:aria-label="title \|\| undefined"/)
})

// The one other raw ion-modal: the must-read notice (a full-page announcement).
const notice = readFileSync(fileURLToPath(new URL("../../MustReadNotice.vue", import.meta.url)), "utf8")
const noticeHost = notice.match(/<ion-modal\b[^>]*>/)?.[0] ?? ""

test("the must-read notice names its ion-modal host too", () => {
	assert.ok(noticeHost, "MustReadNotice renders an ion-modal")
	assert.match(noticeHost, /:aria-label="current\?\.title \|\| undefined"/)
})

test("no other raw ion-modal is left unnamed", async () => {
	const { execSync } = await import("node:child_process")
	const root = fileURLToPath(new URL("../../../", import.meta.url))
	const files = execSync(`grep -rl "<ion-modal" ${root} --include=*.vue || true`, { encoding: "utf8" })
		.split("\n")
		.filter(Boolean)
	for (const file of files) {
		const tag = readFileSync(file, "utf8").match(/<ion-modal\b[^>]*>/)?.[0] ?? ""
		assert.match(tag, /:aria-label=/, `${file} renders an unnamed ion-modal`)
	}
})
