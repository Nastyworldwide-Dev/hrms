// Home's fold budget (plan §1, invariant F1).
//
// The goal the owner set is "no scroll at best, but we dont want to against
// screen reso height and width screen size". Those pull against each other, so
// the rule this file enforces is the resolution: a screen is sized against the
// SMALLEST usable height, not against a chosen one.
//
//   USABLE = 100dvh - header - tab bar (64 + 9 + safe-area) - padding
//
// Measured from design/tokens.json, that is ~440px at 360x640 and ~640px at
// 390x844. Design for 440 and every larger phone is a gift of extra list rows.
//
// What went wrong before this file existed: Home was measured at 1382px of
// content against an 844px fold to offer TEN tap targets
// (docs/glass/audit/2026-09-09-app-measure.json), and nothing in the repo
// failed. Worse, that baseline records tabH:0 on all 36 screens because it was
// captured before the bottom nav was repaired, so the true overflow was ~600px
// and the recorded one 538.
//
// Source-asserted: the node runner does not compile SFCs, so this checks the
// structural decisions that produce the height. The pixel truth is
// frontend/e2e/app-measure.mjs at 360x640 — this file is the cheap gate that
// fails the moment the structure regresses.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const home = () => src("../Home.vue")

// C2: 32px x 3 gaps = 96px of air between four panels, on a screen whose
// smallest budget is 440px. The anchor keeps its breathing room; the rest does
// not get to spend a fifth of the small-phone budget on nothing.
test("Home does not spend the small-phone budget on inter-panel gaps", () => {
	const m = home().match(/class="[^"]*\bflex flex-col\b[^"]*"/)
	assert.ok(m, "Home's content column should still be a flex column")
	assert.doesNotMatch(
		m[0],
		/\bgap-8\b/,
		"gap-8 (32px) x3 = 96px between panels; use gap-5 (20px) and keep gap-8 for the anchor only"
	)
})

// C4: two <h1> on one page is a real a11y defect, not a style preference.
// GAppHeader.vue:44 already renders the page's <h1>; CheckInPanel rendered a
// second one for a greeting, which also costs height the anchor needs.
test("CheckInPanel does not render a second h1", () => {
	// Comments are stripped first: the fix documents itself by naming the tag
	// it removed, and a bare /<h1\b/ matched that explanation instead of any
	// markup. A test that its own subject's prose can fail is not a test.
	const markup = src("../../components/CheckInPanel.vue")
		.replace(/<!--[\s\S]*?-->/g, "")
		.replace(/^\s*\/\/.*$/gm, "")
	assert.doesNotMatch(
		markup,
		/<h1[\s>]/,
		"GAppHeader owns the page h1 (GAppHeader.vue:44); a greeting is not a heading"
	)
})

// C4: "1 remote check-in(s) awaiting your approval" + "Tap to review and
// decide." is 11 words for one count and one tap. The row is already
// interactive, so the hint is redundant to a sighted user and noise to a
// screen reader.
// Amended 22 Sep 2026 (2.0 slice 1.3): the banner became a ROW inside
// `NeedsYou`, which carries the same two rules. The rules are what matter, not
// the file that used to hold them.
test("the approvals row does not tell the user to tap what is already a button", () => {
	assert.doesNotMatch(
		src("../../components/NeedsYou.vue"),
		/Tap to review and decide/,
		"the whole banner is interactive; the instruction is noise"
	)
})

// C4 follow-up, from the S1 review. Shortening the banner is right; deleting
// its SCOPE is not. `count` comes from hrms.api.remote_checkin.get_pending_count
// (data/remoteCheckin.js:21) and the row routes to RemoteApprovals only, so the
// banner has no sight of any on-site approval. "check-in(s) to approve" reads as
// if it covered all of them. An approver who trusts that stops looking
// elsewhere, which is the one failure a visibility banner must not cause.
// Brevity is a budget for words, not a licence to drop the qualifier that makes
// the count true.
test("the approvals row names the scope of the count it shows", () => {
	assert.match(
		src("../../components/NeedsYou.vue"),
		/__\("check-ins? outside the area"\)/,
		"the count is check-ins outside the area only (remote_checkin.get_pending_count); say so"
	)
})
