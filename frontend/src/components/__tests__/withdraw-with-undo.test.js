// Withdraw with Undo, not "Are you sure?" (owner, 29 Sep 2026, alpha.21).
// The request leaves the list at once and "Withdrawn · Undo" shows for 5 s;
// the server is asked only when that closes. Leaving the page does it at once.
// Read from source: no SFC compile in node.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const sheet = read("../RequestActionSheet.vue")
const template = sheet.slice(0, sheet.indexOf("<script")).replace(/<!--[\s\S]*?-->/g, "")

test("no 'This cannot be undone' dialog for a withdraw", () => {
	assert.doesNotMatch(template, /Withdraw this request\?/)
	assert.doesNotMatch(sheet, /This removes your draft/)
	assert.match(template, /@click="withdrawWithUndo"/)
})

test("the request is hidden now and the server asked after the window", () => {
	assert.match(sheet, /hideRequest\(name\)/)
	assert.match(sheet, /undoable\(\s*\(\) =>\s*withdraw\.submit/)
	assert.match(sheet, /showUndo\(__\("Withdrawn"\)/)
})

test("Undo puts it back; a failure puts it back and says why", () => {
	assert.match(sheet, /unhideRequest\(name\)/)
	const store = read("../../data/hiddenRequests.js")
	assert.match(store, /export function hideRequest/)
	assert.match(store, /export function unhideRequest/)
})

test("the lists leave out what is hidden", () => {
	const panel = read("../RequestPanel.vue")
	assert.match(panel, /isHidden\(/)
})

test("the Undo bar is announced and reachable", () => {
	const bar = read("../UndoBar.vue")
	assert.match(bar, /role="status"/)
	assert.match(bar, /<button[^>]*type="button"[^>]*@click="undo"/)
	assert.match(read("../../App.vue"), /<UndoBar \/>/)
})
