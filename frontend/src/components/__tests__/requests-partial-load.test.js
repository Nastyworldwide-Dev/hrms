// "Your last 5" merges six request lists. When one of them fails but others have rows, the list
// looked complete (RequestPanel ceiling, alpha.41 S7): a person missing one kind of request was
// never told. The panel now says so under the rows, with a way to try again.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const panel = readFileSync(fileURLToPath(new URL("../RequestPanel.vue", import.meta.url)), "utf8")
const template = panel.slice(panel.indexOf("<template>"), panel.indexOf("</template>\n\n<script"))
const script = panel.slice(panel.indexOf("<script"))

test("a list that failed while others have rows is said, not hidden", () => {
	// whitespace-blind: the formatter decides where the line breaks
	const flat = script.replace(/\s+/g, "")
	assert.ok(
		flat.includes(
			"constpartlyLoaded=computed(()=>lastFive.value.length>0&&MY_REQUEST_LISTS.some((list)=>list.error))"
		),
		"partlyLoaded is: rows shown AND one list failed"
	)
	const line = template.match(/<p[^>]*v-if="partlyLoaded"[^>]*>[\s\S]*?<\/p>/)?.[0]
	assert.ok(line, "a line shown only when partly loaded")
	assert.match(line, /role="status"/)
	assert.match(line, /Some requests didn't load\./)
	assert.match(line, /@click="lastFiveResource\.reload\(\)"/)
	assert.match(line, /Try again/)
})

test("the old ceiling note is gone with the gap it named", () => {
	assert.doesNotMatch(script, /ceiling: a partial failure with rows reads as complete/)
})
