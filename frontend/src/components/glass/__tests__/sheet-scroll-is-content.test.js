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

test("the sheet body keeps the panel's own inset — a real token, not a fallback", () => {
	// review of 6a7e9341f: `var(--g-pad-panel-x, 13px)` named a token that does
	// not exist, so every sheet's content sat 3 px tighter than its 16 px head.
	const css = readFileSync(new URL("../../../theme/glass-components.css", import.meta.url), "utf8")
	const tokens = readFileSync(new URL("../../../theme/glass.css", import.meta.url), "utf8")
	const body = css.slice(css.indexOf(".g-sheet__body {"), css.indexOf("}", css.indexOf(".g-sheet__body {")))
	for (const [, name] of body.matchAll(/var\((--[\w-]+)/g)) {
		assert.match(tokens, new RegExp(`${name}:`), `${name} is defined`)
	}
	assert.match(body, /padding: 0 var\(--g-pad-panel\);/)
})

test("one rule owns the head, and it no longer bleeds past a padless sheet", () => {
	// design review of 6a7e9341f: a second .g-sheet__head block was overridden by
	// the old one, whose -16 px side margins now made the head 32 px wider than
	// the sheet.
	const css = readFileSync(new URL("../../../theme/glass-components.css", import.meta.url), "utf8")
	const heads = css.match(/^\.g-sheet__head \{[^}]*\}/gm) || []
	assert.equal(heads.length, 1)
	assert.doesNotMatch(heads[0], /calc\(-1 \* var\(--g-pad-panel\)\)/)
	assert.doesNotMatch(heads[0], /position: sticky/)
})

test("a keyboard user can reach and scroll the sheet's content", () => {
	assert.match(modal, /<ion-content[^>]*tabindex="0"/)
})
