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
