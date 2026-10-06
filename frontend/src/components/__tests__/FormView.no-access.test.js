// A request someone may not open (403 on its read) showed "Could not open this
// leave request. It may have been removed, or you may not have access. Check your
// connection and try again." with Try again: a retry that cannot work, the same
// glitch-like wording alpha.37 B2 removed from ResourceError. The shell now says
// what ResourceError says for a refusal: "You can't open this." with a way back.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const src = readFileSync(new URL("../FormView.vue", import.meta.url), "utf8")
const template = src.split("<script")[0]

test("a refused read says 'You can't open this.' and offers Back, not Try again", () => {
	assert.match(src, /import \{ isNoAccess \} from "@\/utils\/sessionLost"/)
	assert.match(src, /const noAccess = computed\(\(\) =>\s*isNoAccess\(documentResource\.get\.error/)
	assert.match(template, /v-else-if="noAccess"[\s\S]*?You can\\?'t open this\./)
	const block = template.match(/v-else-if="noAccess"[\s\S]*?<\/GEmptyState>/)?.[0] ?? ""
	assert.match(block, /goBackOrHome\(router\)/, "a way back")
	assert.doesNotMatch(block, /Try again/, "no retry that cannot work")
})

test("any other failed read keeps its wording and Try again", () => {
	assert.match(template, /Could not open this \{0\}/)
	assert.match(template, /reloadDoc\(\)/)
})
