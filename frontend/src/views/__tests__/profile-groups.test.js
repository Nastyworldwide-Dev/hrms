// Profile, now "You" (audit-pages §4; once four groups, revamp §7 slice D3).
//
// It was a single undifferentiated column of nine rows, each a hand-built div
// with its own padding, border and hover — 17 of the app's 103 stray pixel
// values lived on this one screen. Somebody looking for "change my password"
// had to read all nine, and one of them (Change Password) was not even there:
// it was a row inside Settings.
//
// The four groups answer four different questions — who am I, where do I
// work, how does the app behave, how do I get out — which is what makes them
// groups rather than a divided list.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")

const code = (text) =>
	text
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))

const view = code(read("views/Profile.vue"))

test("the rows come from the system's list components", () => {
	// The hand-built rows carried their own padding, dividers and hover, which
	// is why they drifted from every other list in the app — and why this one
	// screen held 17 stray pixel values.
	assert.match(view, /<GListPanel>/)
	assert.match(view, /<GListRow/)
	assert.doesNotMatch(view, /class="flex flex-row cursor-pointer p-4/, "no hand-built rows")
})

test("the version is on the screen people report defects from", () => {
	// Every phone-side defect this month began with "which version are you
	// on". A plain line on You now (audit-pages §4), not a button.
	assert.match(view, /Version \{0\} · \{1\}/)
	assert.match(view, /__APP_BUILD__/, "the compile-time stamp")
	assert.match(code(read("utils/diagnostics.js")), /__APP_BUILD__/)
})

test("change password has its own row", () => {
	// It was a row inside Settings, which is two taps and a guess. It is the
	// single most-looked-for thing on an account screen.
	assert.match(view, /key: "password"/)
	assert.match(view, /name: "ChangePassword"/)
})

test("nothing was lost in the You rework (audit-pages §4)", () => {
	// Every destination is still reachable: from You, or where the plan moved it.
	for (const destination of ["Approvals", "ChangePassword"]) {
		assert.match(view, new RegExp(`name: "${destination}"`), `${destination} survives`)
	}
	assert.match(
		read("views/helpdesk/HelpdeskHub.vue"),
		/<WhoToAsk/,
		"HR contacts moved to Help (a Who to ask sheet since alpha.5)"
	)
	assert.match(view, /const DETAILS = \[/, "the details sheet")
})

test("the role gate is still the server's verdict", () => {
	// `isApprover` is a RESOURCE — answered by the backend — not a role string
	// read here. The regroup moved the row; it did not move the decision.
	assert.match(view, /isApprover\.data/)
	assert.doesNotMatch(view, /"HR Manager"|"HR User"/, "no role literal")
})

// alpha.6 B3 (owner screenshot, 24 Sep 2026): "the Switch button, notification
// and shift reminders are odd design and placement. Doesnt follow how ios 26
// does." The switches sat on the LEFT, outside any group, with their hints
// floating underneath. Apple HIG Toggles: a switch lives in a list row, the
// row text is its label, the switch trails; guidance goes in the group footer.
// SUPERSEDED 26 Sep 2026 (alpha.12, owner ruling R4): no Appearance row at
// all — Apple (dark-mode): "Avoid offering an app-specific appearance setting."
test("app settings are one grouped list of switch rows, with no Appearance picker", () => {
	const group = view.slice(view.indexOf('class="g-form-group g-you-settings"'))
	assert.ok(group.length > 0, "the settings group exists")
	const block = group.slice(0, group.indexOf("</div>\n"))
	assert.doesNotMatch(block, /Appearance/)
	assert.match(view, /class="g-form-row__switch"[\s\S]*?Notifications|Notifications[\s\S]*?class="g-form-row__switch"/)
	assert.doesNotMatch(view, /<GSegmented/, "no three-button theme bar")
	assert.doesNotMatch(view, /g-switch-row/, "no floating switch rows")
})

test("the hint is the group footer, not a line under a switch", () => {
	assert.match(view, /class="g-form-footer"/)
})

test("log out is a red row, not a bordered button (HIG: destructive = red text)", () => {
	assert.match(view, /class="g-form-row g-form-row--action g-form-row--destructive"/)
})
