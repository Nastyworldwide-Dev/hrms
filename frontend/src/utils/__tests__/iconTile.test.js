// alpha.7 Phase 3 (plan §7, owner Q2 = yes): like iOS Settings, each kind of
// thing has ONE coloured tile with a white symbol, reused everywhere it
// appears (Requests sheet, Needs you, More, notifications). Colour carries
// the kind; the word carries the meaning (never colour alone).
import { test } from "node:test"
import assert from "node:assert/strict"
import { TILE, tileFor } from "../iconTile.js"

test("the §7 palette, Apple's iOS system colours", () => {
	assert.equal(TILE.leave, "#30D158")
	assert.equal(TILE.overtime, "#FF9230")
	assert.equal(TILE.expense, "#0091FF")
	assert.equal(TILE.shift, "#6D7CFF")
	assert.equal(TILE.fix, "#40C8E0")
	assert.equal(TILE.help, "#0091FF")
	assert.equal(TILE.sop, "#B78A66")
	assert.equal(TILE.announcement, "#FF4245")
	assert.equal(TILE.holiday, "#FF4245")
})

test("a doctype resolves to its kind's tile", () => {
	assert.equal(tileFor("Leave Application"), TILE.leave)
	assert.equal(tileFor("Compensatory Leave Request"), TILE.leave)
	assert.equal(tileFor("OT Request"), TILE.overtime)
	assert.equal(tileFor("Expense Claim"), TILE.expense)
	assert.equal(tileFor("Shift Request"), TILE.shift)
	assert.equal(tileFor("Attendance Request"), TILE.fix)
	assert.equal(tileFor("leave"), TILE.leave, "a Requests-sheet key works too")
})

test("an unknown kind gets the neutral tile, never a wrong colour", () => {
	assert.equal(tileFor("Something New"), TILE.neutral)
	assert.equal(tileFor(undefined), TILE.neutral)
})
