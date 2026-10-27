// The one rule for a notice's row, on Home and on the board (owner-approved mockup, 27 Oct 2026):
// which badge it wears, what the line under the title says, which section it sits in. Real calls,
// no source matching: the node runner cannot compile the pages, but it can run these.
import { test } from "node:test"
import assert from "node:assert/strict"
import dayjs from "dayjs"

import { badgeFor, boardSections, noticeDates, subtitle, trailAge } from "../announcementRow.js"

// a translator that is visibly applied, with the {0} placeholders the app's __ fills
const __ = (text, args = []) => `~${text.replace(/\{(\d)\}/g, (_, i) => args[i])}`
const ageOf = (date) => `age(${date})`

test("an urgent notice you have not opened says Urgent, even when it also asks for a confirmation", () => {
	assert.deepEqual(badgeFor({ urgent: true, read: false }, __), {
		variant: "urgent",
		text: "~Urgent",
	})
	assert.deepEqual(badgeFor({ urgent: true, read: false, needs_acknowledgement: true }, __), {
		variant: "urgent",
		text: "~Urgent",
	})
})

test("a notice that asks for a confirmation says Confirm, read or not, until it is confirmed", () => {
	assert.deepEqual(badgeFor({ needs_acknowledgement: true, read: true }, __), {
		variant: "open",
		text: "~Confirm",
	})
	assert.deepEqual(badgeFor({ urgent: true, read: true, needs_acknowledgement: true }, __), {
		variant: "open",
		text: "~Confirm",
	})
})

test("an unopened notice says New; an opened one wears nothing", () => {
	assert.deepEqual(badgeFor({ read: false }, __), { variant: "accent", text: "~New" })
	assert.equal(badgeFor({ read: true }, __), null)
	assert.equal(badgeFor({ urgent: true, read: true }, __), null, "urgent is about what is unread")
})

test("the line under the title is HR's summary, never text cut from the body", () => {
	const card = {
		summary: "Read it by Friday.",
		body: "<p>long</p>",
		needs_acknowledgement: true,
		publish_from: "2026-10-25",
	}
	assert.equal(subtitle(card, __, ageOf), "Read it by Friday.")
})

test("with no summary: a must-read says it needs you, anything else says how old it is", () => {
	assert.equal(
		subtitle({ needs_acknowledgement: true, publish_from: "2026-10-25" }, __, ageOf),
		"~Needs your confirmation"
	)
	assert.equal(subtitle({ publish_from: "2026-10-25" }, __, ageOf), "age(2026-10-25)")
	assert.equal(subtitle({}, __, ageOf), "", "no date, no age")
})

test("the age on the right says what the line under the title does not", () => {
	const dated = { publish_from: "2026-10-25" }
	assert.equal(trailAge({ ...dated, summary: "Read it." }, __, ageOf), "age(2026-10-25)")
	assert.equal(trailAge({ ...dated, needs_acknowledgement: true }, __, ageOf), "age(2026-10-25)")
	assert.equal(trailAge(dated, __, ageOf), "", "the line under the title already IS the age")
	assert.equal(trailAge({ summary: "Read it." }, __, ageOf), "", "no date, no age")
})

test("the board splits into 'to confirm' and 'latest', urgent first, then the server's order", () => {
	const rows = [
		{ name: "plain1" },
		{ name: "urgent1", urgent: true },
		{ name: "must", needs_acknowledgement: true },
		{ name: "plain2" },
		{ name: "urgent2", urgent: true, read: true },
		{ name: "must2", needs_acknowledgement: true, urgent: true },
	]
	const { toConfirm, latest } = boardSections(rows)
	assert.deepEqual(
		toConfirm.map((r) => r.name),
		["must", "must2"],
		"server order kept"
	)
	assert.deepEqual(
		latest.map((r) => r.name),
		["urgent1", "urgent2", "plain1", "plain2"]
	)
})

test("a confirmed must-read is just another notice, and no data is an empty board", () => {
	const { toConfirm, latest } = boardSections([
		{ name: "done", needs_acknowledgement: false, acknowledge_required: true },
	])
	assert.deepEqual([toConfirm.length, latest.length], [0, 1])
	assert.deepEqual(boardSections(undefined), { toConfirm: [], latest: [] })
	assert.deepEqual(boardSections([]), { toConfirm: [], latest: [] })
})

test("the notice's one meta line: posted and shown until, as D MMM", () => {
	const fmt = (d) => dayjs(d).format("D MMM")
	assert.equal(
		noticeDates({ publish_from: "2026-10-25", publish_until: "2026-11-14" }, __, fmt),
		"~Posted 25 Oct · Shown until 14 Nov"
	)
	assert.equal(noticeDates({ publish_from: "2026-10-25" }, __, fmt), "~Posted 25 Oct")
	assert.equal(noticeDates({ publish_until: "2026-11-14" }, __, fmt), "~Shown until 14 Nov")
	assert.equal(noticeDates({}, __, fmt), "", "nothing to say, no line")
})
