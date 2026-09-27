// alpha.13 slice 5 (owner: "gooo" on mockups/mockup-nadi-a13-feedback.html).
// Apple's own effects, once each, all stopped by Reduce Motion:
// 1. a decision draws its mark on the button pressed, then the sheet closes
//    and the list closes the gap (Draw On, then content leaves);
// 2. numbers people watch roll to their new value (content replace);
// 3. every button shrinks a little and dims while pressed (Apple buttons:
//    "a pressed state always").
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const css = read("../../theme/glass-components.css")

test("a decision draws its mark on the button before the sheet closes", () => {
	const sheet = read("../RequestActionSheet.vue")
	assert.match(sheet, /decidedAs\.value = status/)
	assert.match(sheet, /class="g-btn__tick"/)
	assert.match(sheet, /setTimeout\(\s*\(\) =>\s*modalController\.dismiss\(\)/)
	const checkin = read("../CheckinDecisionSheet.vue")
	assert.match(checkin, /decidedAs\.value = /)
})

test("the approvals list closes the gap instead of jumping", () => {
	const view = read("../../views/Approvals.vue")
	assert.match(view, /<TransitionGroup name="g-leave"/)
	assert.match(css, /\.g-leave-leave-active[^{]*\{[^}]*var\(--g-motion-symbol-duration\)/)
})

test("numbers roll: one GRollNumber used for leave left, overtime and the unread count", () => {
	const roll = read("../glass/GRollNumber.vue")
	assert.match(roll, /<Transition name="g-roll"/)
	for (const [file, why] of [
		["../glass/GBalanceCard.vue", "leave left"],
		["../HomeWeek.vue", "overtime to claim"],
	]) {
		assert.match(read(file), /<GRollNumber/, `${why} rolls`)
	}
})

test("every button answers the finger", () => {
	// the shrink existed (0.98); the dim is new — Apple's pressed state is both
	const rule = css.slice(css.indexOf(".g-btn:active:not(.g-btn--disabled)"))
	const body = rule.slice(0, rule.indexOf("}"))
	assert.match(body, /transform:\s*scale\(0\.98\)/)
	assert.match(body, /opacity:\s*0\.8/)
})
