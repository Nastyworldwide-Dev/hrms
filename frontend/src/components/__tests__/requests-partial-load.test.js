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

test("the line is wired to the shared rule and retries in place", () => {
	// the rule itself is tested by behaviour in utils/__tests__/partlyLoaded.test.js
	const flat = script.replace(/\s+/g, "")
	assert.ok(
		flat.includes("partlyLoaded(lastFive.value.length,MY_REQUEST_LISTS)"),
		"uses the shared rule"
	)
	const region = template.match(/<div role="status">[\s\S]*?<\/div>/)?.[0]
	assert.ok(region, "the live region is always in the page")
	assert.match(region, /v-if="isPartlyLoaded"/)
	assert.match(region, /Some requests didn't load\./)
	assert.match(region, /@click="retryLastFive"/)
})

test("the old ceiling note is gone with the gap it named", () => {
	assert.doesNotMatch(script, /ceiling: a partial failure with rows reads as complete/)
})
