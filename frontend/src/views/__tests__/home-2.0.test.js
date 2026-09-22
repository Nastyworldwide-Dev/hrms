// Home, once the tab bar says what Home is for (2.0 slice 1.3, UX_PLAN §3.1).
//
// The plan's Home is four things in one order: greeting and date, the check-in
// card, "NEEDS YOU", then your requests. What shipped is a different order with
// a different middle: an approvals banner, the check-in card, seven quick
// links, then the request panel.
//
// THE QUICK LINKS ARE THE CHANGE. They were Home's answer to "how do I start a
// request?" — and that question now has a screen of its own (slice 0.1's
// Requests tab), reachable in one tap from the bar. Keeping them on Home meant
// Home's largest block existed to answer a question the navigation answers,
// while the thing the plan puts in that slot — what needs the employee TODAY —
// was a single conditional banner above the fold.
//
// So Home becomes: what is happening (check-in), what needs you, what you
// asked for. Nothing is lost: every quick link lives on Requests, one tap away
// and one tap from anywhere.
//
// WHAT MUST NOT REGRESS. Home is a tab root, so §15's six-surface budget and
// the fold budget both apply, and the fold budget is the one this slice exists
// to improve rather than merely not worsen.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")

function template(file) {
	const text = read(file)
	return text
		.slice(0, text.indexOf("<script"))
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
}

test("Home reads in the plan's order", () => {
	// §3.1: check-in, then what needs you, then your requests. The order is the
	// screen's argument — what is happening now, what is waiting on you, what
	// you already asked for.
	const body = template("views/Home.vue")
	const order = ["CheckInPanel", "NeedsYou", "RequestPanel"]
	const at = order.map((name) => body.indexOf(`<${name}`))
	for (const [i, name] of order.entries()) {
		assert.ok(at[i] > 0, `${name} should be on Home`)
		if (i) assert.ok(at[i] > at[i - 1], `${name} comes after ${order[i - 1]}`)
	}
})

test("the quick links moved to the screen that is for them", () => {
	// Not deleted — moved. A link nobody can reach is worse than a crowded Home.
	assert.doesNotMatch(template("views/Home.vue"), /<QuickLinks/, "Home no longer starts requests")
	assert.match(template("views/Requests.vue"), /<QuickLinks/, "Requests does")
})

test("nothing Home offered became unreachable", () => {
	// Every destination Home's quick links named must still be named somewhere.
	// This is the one check that would catch a link quietly lost in the move.
	const requests = read("views/Requests.vue")
	for (const route of [
		"AttendanceRequestFormView",
		"ShiftRequestFormView",
		"LeaveApplicationFormView",
		"ExpenseClaimFormView",
	]) {
		assert.match(requests, new RegExp(route), `${route} survived the move`)
	}
})

test("what needs you is one block, not a banner and a hope", () => {
	// `PendingApprovalsBanner` answered only "you have approvals waiting". The
	// plan's row is wider — approvals, geofence reviews, issue replies — and
	// its shape is "3 rows then N more", the same bound the request panel
	// already uses. One component, so a second kind of thing joining the list
	// is a row rather than another conditional banner.
	const needs = read("components/NeedsYou.vue")
	assert.match(needs, /role="status"|aria-/, "it announces itself when it appears")
	assert.match(needs, /HOME_ROWS|slice\(0,/, "bounded, like the request panel")
})

test("an empty needs-you says nothing at all", () => {
	// §11: empty is a state, and for THIS block the right empty state is
	// absence. A permanent "nothing needs you" row is a row that is wrong most
	// of the time and costs the fold every day.
	const needs = read("components/NeedsYou.vue")
	assert.match(
		needs,
		/v-if="[^"]*(items|rows|count)[^"]*\.length|v-if="[^"]*any/,
		"it renders only when it has something"
	)
})

test("Home still fits its budget", () => {
	// The fold budget (home-fold-budget.test.js) and §15's six surfaces both
	// still apply. This slice REMOVES the largest block, so the numbers can
	// only improve — what this pins is that the replacement did not quietly
	// add a surface.
	const body = template("views/Home.vue")
	assert.doesNotMatch(
		body,
		/g-glass/,
		"Home composes primitives; it does not paint its own surface"
	)
})
