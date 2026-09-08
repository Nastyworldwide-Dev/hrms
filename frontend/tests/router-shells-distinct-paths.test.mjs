import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const source = readFileSync(
	fileURLToPath(new URL("../src/router/index.js", import.meta.url)),
	"utf8"
)

// Ionic's nested <ion-router-outlet> claims a navigation when the first matched
// route's PATH STRING equals the path it was mounted under. Two shells mounted
// at "/" therefore both render every child route: the tab shell's hidden outlet
// pushed a leave application (a FormShell child, opened from Notifications)
// onto the Home tab's stack, where it sat on top of Home after Back and after
// tapping the Home tab. The shells must sit at distinct paths.

// TabbedView is imported statically, FormShell lazily — accept either form
const shellPath = (view) => {
	const match = source.match(
		new RegExp(
			`path: "([^"]*)",\\s*component: (?:${view}|\\(\\) => import\\("@/views/${view}\\.vue"\\))`
		)
	)
	assert.ok(match, `${view} is a routed shell`)
	return match[1]
}

test("the tab shell and the form shell are mounted at distinct paths", () => {
	const tabs = shellPath("TabbedView")
	const forms = shellPath("FormShell")
	assert.equal(tabs, "/")
	assert.notEqual(forms, "/")
	assert.notEqual(forms, tabs)
})

test("form routes keep their absolute URLs under the moved shell", () => {
	assert.match(source, /path: "\/form",\s*component: \(\) => import\("@\/views\/FormShell\.vue"\)/)
	// every leaf route file declares absolute paths — the shell prefix is inert
	const leaves = readFileSync(
		fileURLToPath(new URL("../src/router/leaves.js", import.meta.url)),
		"utf8"
	)
	assert.match(leaves, /path: "\/leave-applications\/:id"/)
})
