// alpha.7 Phase 3 (plan §5.5; reviews B1, B6): a sent request reads as
// label / value rows (SwiftUI LabeledContent): no chevrons, no pickers, no
// pills, no switches. A read-only yes/no is the word "Yes"/"No"; a date is
// written out ("15 Sep 2026"). Cancel is a red text row, not a capsule.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const field = read("../FormField.vue")
const root = postcss.parse(read("../../theme/glass-components.css"))
const has = (sel) => {
	let found = false
	root.walkRules((r) => {
		if (r.selectors?.includes(sel)) found = true
	})
	return found
}

test("a read-only row is marked, and yes/no and dates are plain words", () => {
	assert.match(field, /'g-form-row--readonly': isReadOnly/)
	assert.match(field, /v-if="isReadOnly && \['Check', 'Date'\]\.includes\(props\.fieldtype\)"/)
	assert.match(field, /class="g-form-row__value"/)
})

test("read-only rows hide every control affordance", () => {
	assert.ok(has(".g-form-row--readonly .g-select__chevron"))
	assert.ok(has(".g-form-row--readonly .g-linkpick__chevron"))
})

test("Cancel on a sent request is a red row", () => {
	const form = read("../FormView.vue")
	assert.match(form, /class="g-form-row g-form-row--action g-form-row--destructive"[\s\S]{0,200}__\("Cancel request"\)/)
})

test("status is said once: the header chip, not a row too", () => {
	const form = read("../FormView.vue")
	assert.match(form, /const STATUS_ROWS = \["status", "approval_status"\]/)
	assert.match(form, /!\(STATUS_ROWS\.includes\(f\.fieldname\) && isFieldReadOnly\(f\)\)/)
})
