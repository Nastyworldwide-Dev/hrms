// Scrolling inside a sheet moved the sheet (senior report, 28 Sep 2026: "scrolling
// inside sheet move the sheet as well, jumpy jumpy"). Measured in a phone
// browser before this fix: on the day sheet a downward drag after scrolling
// moved the whole sheet 100 px while the list scrolled; on the holidays sheet a
// gentle drag in the list closed it.
//
// Ionic 7's sheet gesture (ion-modal createSheetGesture.canStart) yields to the
// content only when the drag starts inside an `ion-content` element — it tests
// `target.closest('ion-content')`, nothing else. Our scroller was a plain div,
// so every drag was taken as "move the sheet". The content now scrolls inside
// an ion-content; the grabber and title bar above it still drag the sheet.
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { test } from "node:test"

const modal = readFileSync(new URL("../GModal.vue", import.meta.url), "utf8")

test("Ionic's sheet gesture still yields to ion-content, and only to it", () => {
	const gesture = readFileSync(
		new URL("../../../../node_modules/@ionic/core/components/ion-modal.js", import.meta.url),
		"utf8"
	)
	const canStart = gesture.slice(gesture.indexOf("const createSheetGesture"))
	assert.match(canStart, /detail\.event\.target\.closest\('ion-content'\)/)
})

test("the sheet's content scrolls inside an ion-content, the head stays out of it", () => {
	const template = modal.slice(modal.indexOf("<template>"), modal.indexOf("</template>"))
	const head = template.indexOf('class="g-sheet__head"')
	const content = template.indexOf("<ion-content")
	assert.ok(content > 0, "the content is an ion-content")
	assert.ok(head > 0 && head < content, "the draggable head sits above it, outside")
	assert.match(template, /<ion-content[^>]*class="g-sheet__content"/)
	assert.match(modal, /IonContent/, "imported from @ionic/vue")
})
