// alpha.7 Phase 3 (plan §5.3; reviews A6, A14, A15): on iOS a list is never
// rows loose on the page. "Your last 5" is ONE inset group; its header sits
// on the group; "See all" is the group's last row.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const list = read("../RequestList.vue")
const panel = read("../RequestPanel.vue")

test("the compact list is one inset group of rows", () => {
	assert.match(list, /v-else-if="props\.items\?\.length && props\.compact"/)
	assert.match(list, /<div class="g-form-group">\s*<button\s+v-for="link in props\.items"/)
	assert.match(list, /class="g-form-row g-form-row--action g-req-row"/)
})

test("See all is the group's last row, not a loose link below", () => {
	assert.match(list, /<slot name="footer" \/>/)
	assert.match(panel, /<template #footer>[\s\S]*class="g-form-row g-form-row--action g-seeall"/)
})
