// Requests jumped 0.39 on first load (audit F-12 / APP-28; CLS limit 0.1,
// measured live 23 Sep): the balance strip rendered NOTHING until its data
// arrived, then pushed "New request" and the list down. While the first read
// is in flight it holds its place with the grid's own skeleton (F-7: one
// loading pattern, skeletons).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const source = readFileSync(
	fileURLToPath(new URL("../RequestBalances.vue", import.meta.url)),
	"utf8"
)
const template = source.slice(0, source.indexOf("<script"))

test("the first load holds its place with a skeleton grid", () => {
	// Sized like the typical finished strip: a leave grid and two door rows.
	assert.match(
		template,
		/v-else-if="firstLoad"[\s\S]*?<GBalanceGrid loading :cells="4" \/>[\s\S]*?<GListPanel loading :rows="2" \/>/
	)
	assert.match(
		source,
		/const firstLoad = computed\(\(\) => requestsSummary\.loading && !requestsSummary\.data\)/
	)
})
