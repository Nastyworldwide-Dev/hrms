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
	assert.match(src, /import \{ isGone \} from "@\/utils\/requestFailure"/)
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

// Persona crawl, 25 Oct 2026: a deleted record read as a connection glitch with a retry.
test("a record that is gone says so and offers Back, not Try again", () => {
	assert.match(src, /const gone = computed\(\(\) =>\s*isGone\(documentResource\.get\.error/)
	const block = template.match(/v-else-if="gone"[\s\S]*?<\/GEmptyState>/)?.[0] ?? ""
	assert.match(block, /data-no-access/, "the toast seam sees the screen already said it")
	assert.match(block, /This \{0\} is no longer here/)
	assert.match(block, /goBackOrHome\(router\)/)
	assert.doesNotMatch(block, /Try again/)
})


// Persona crawl, 25 Oct 2026: every failed open (gone, refused, offline) also logged a
// "[diagnostics] vue.render" crash: onMounted awaited the failed read, so the rejection escaped
// into Vue's error handler. The card above already says what happened; the start-up stops.
test("a failed first read stops the form's start-up instead of throwing out of onMounted", () => {
	const mount = src.match(/onMounted\(async \(\) => \{[\s\S]*?\n\}\)/)?.[0] ?? ""
	assert.match(mount, /await documentResource\.get\.promise\?\.catch\?\.\(\(\) => null\)/)
	assert.match(mount, /if \(documentResource\.get\.error\) return/)
})

// Review of c3b699efe: a first open that failed (offline, 5xx) skipped the form's set-up, and
// Try again only re-read the document, so after the network came back the form drew without
// its write permissions, attachments or workflow: every field read-only, no Approve/Reject.
// The set-up is one function; Try again runs it when the first open never did.
test("Try again finishes a set-up that a failed first open skipped", () => {
	const setup = src.match(/async function setUpForm\(\) \{[\s\S]*?\n\}/)?.[0] ?? ""
	for (const step of ["docPermissions.reload", "permittedWriteFields.reload", "attachedFiles.reload", "setFormattedCurrency", "useWorkflow"])
		assert.ok(setup.includes(step), `setUpForm runs ${step}`)
	const mount = src.match(/onMounted\(async \(\) => \{[\s\S]*?\n\}\)/)?.[0] ?? ""
	assert.match(mount, /await setUpForm\(\)/)
	const reload = src.match(/async function reloadDoc\(\) \{[\s\S]*?\n\}/)?.[0] ?? ""
	assert.match(reload, /await documentResource\.reload\(\)\?\.catch\?\.\(\(\) => null\)/)
	assert.match(reload, /if \(documentResource\.get\.error\) return/)
	assert.match(reload, /if \(props\.id && !isSetUp\) await setUpForm\(\)/)
})
