// "1 leave request to approve" on Home opened the leave list on "My leaves",
// which was empty; the request to decide sat behind a second tab (audit P0-9).
// A list opens on the tab its route asks for, so a door lands on its room.
// The lists' tabs are ["My Leaves", "Team Leaves"] — the team tab is always
// the second, and it only appears once the approver check has loaded.
import { test } from "node:test"
import assert from "node:assert/strict"

import { initialListTab } from "../listTab.js"

const both = ["My Leaves", "Team Leaves"]

test("with no request, the first tab", () => {
	assert.equal(initialListTab(both, undefined), "My Leaves")
})

test("?tab=team opens the team tab", () => {
	assert.equal(initialListTab(both, "team"), "Team Leaves")
})

test("before the team tab exists, the first tab (the list re-asks when it appears)", () => {
	assert.equal(initialListTab(["My Leaves"], "team"), "My Leaves")
})

test("an unknown or forged request falls back to the first", () => {
	assert.equal(initialListTab(both, "everyone"), "My Leaves")
	assert.equal(initialListTab(both, ["team"]), "My Leaves")
})

test("object tabs use their key", () => {
	assert.equal(initialListTab([{ key: "mine" }, { key: "theirs" }], "team"), "theirs")
})

test("a list with no tabs has no tab", () => {
	assert.equal(initialListTab(undefined, "team"), undefined)
})

import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8")

test("Home's waiting rows ask their list for the team tab", () => {
	assert.match(
		read("../../components/NeedsYou.vue"),
		/router\.push\(\{ name: row\.route, query: \{ tab: "team" \} \}\)/
	)
})

test("the list opens on the tab its route asks for", () => {
	assert.match(
		read("../../components/ListView.vue"),
		/initialListTab\(props\.tabButtons, route\.query\.tab\)/
	)
})
