// Owner-approved Home, 23 Sep 2026: one screen, five blocks, every block
// ALWAYS renders and says why it is empty. Order: Today (NowBar +
// CheckInPanel), News (Announcements, moved up "so everyone will notice…
// kinda like news"), This week, Coming up, Waiting on you (NeedsYou).
// Source-asserted: the node runner does not compile SFCs.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const templateOf = (text) =>
	text.slice(0, text.indexOf("<script")).replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))

const home = read("../Home.vue")
const week = read("../../components/HomeWeek.vue")
const comingUp = read("../../components/HomeComingUp.vue")
const data = read("../../data/home.js")

test("Home reads Today, News, This week, Coming up, Waiting on you", () => {
	const body = templateOf(home)
	// alpha.7 (25 Sep): Announcements first, then Today, Needs you, Your week.
	const order = ["Announcements", "NowBar", "CheckInPanel", "NeedsYou", "HomeWeek", "HomeComingUp"]
	const at = order.map((name) => body.indexOf(`<${name}`))
	for (const [i, name] of order.entries()) {
		assert.ok(at[i] > 0, `${name} should be on Home`)
		if (i) assert.ok(at[i] > at[i - 1], `${name} comes after ${order[i - 1]}`)
	}
})

for (const [name, src, resource, empty] of [
	["This week", week, "homeWeek", "Nothing to claim this week."],
	["Coming up", comingUp, "homeComingUp", "Nothing booked."],
]) {
	test(`${name} always renders: eyebrow, skeleton, error line, empty line`, () => {
		const t = templateOf(src)
		assert.doesNotMatch(t.split("\n").find((l) => /<div/.test(l)) || "", /v-if/, "the root never hides")
		// Since the surfaces fix, both rows share ONE panel under "Your week"
		// on Home, which owns the title and the skeleton; each row keeps its
		// own error line and empty line.
		const home = read("../Home.vue")
		assert.match(home, /__\("Your week"\)/, "one eyebrow for both rows")
		assert.match(home, /<GListPanel\s+:loading=/, "one skeleton for both rows")
		assert.match(t, new RegExp(`v-if="${resource}\\.error"`), "a failed call is one plain line")
		assert.match(src, new RegExp(empty.replace(/\./g, "\\.")), "says why it is empty")
		assert.match(t, /<GListRow/)
	})
}

test("This week taps through to the overtime form", () => {
	assert.match(week, /name: "OTRequestFormView"/)
	assert.match(week, /overtime to claim/)
})

test("Coming up names the next public holiday when nothing is booked", () => {
	assert.match(comingUp, /Nothing booked\. Next public holiday: \{0\} · \{1\}/)
})

test("both resources are personal and call the new home endpoints", () => {
	assert.match(data, /url: "hrms\.api\.home\.get_home_week"/)
	assert.match(data, /url: "hrms\.api\.home\.get_home_coming_up"/)
	assert.equal((data.match(/personalCacheKey\(/g) || []).length, 2)
})

test("pull-to-refresh reloads the two new blocks too", () => {
	const body = home.slice(home.indexOf("async function refresh"), home.indexOf("</script>"))
	for (const resource of ["homeWeek", "homeComingUp"]) {
		assert.match(body, new RegExp(`${resource}\\.reload\\(`), resource)
	}
})

// Surfaces gate (§15.1, Home was 8/6 after the new blocks): This week and
// Coming up share ONE panel under "Your week"; the announcement error is a
// plain line, not a banner panel.
test("Home stays inside its six glass surfaces", () => {
	const home = read("../Home.vue")
	assert.match(home, /__\("Your week"\)[\s\S]*<GListPanel[^>]*>\s*<HomeWeek \/>\s*<HomeComingUp \/>\s*<\/GListPanel>/)
	assert.doesNotMatch(read("../../components/Announcements.vue"), /<GBanner/)
})
