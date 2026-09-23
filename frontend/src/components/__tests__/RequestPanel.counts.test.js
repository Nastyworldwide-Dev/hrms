// Audit P0-8: the filter chips counted only the rows already loaded (the
// newest ten of each type). On "My requests" they now show the server's
// count over every request. Source-asserted (no SFC compile in node).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../RequestPanel.vue", import.meta.url)), "utf8")

test("the panel reads the server's counts", () => {
	assert.match(src, /import \{ myRequestCounts \} from "@\/data\/requestCounts"/)
})

test("on My requests, a chip shows the server count, not the loaded rows", () => {
	const at = src.indexOf("const filterCounts = computed(")
	const body = src.slice(at, src.indexOf("\n})", at))
	assert.match(body, /activeTab\.value === "My Requests" && myRequestCounts\.data/)
})

test("the counts reload with the lists", () => {
	const lists = readFileSync(
		fileURLToPath(new URL("../../data/requestLists.js", import.meta.url)),
		"utf8"
	)
	assert.match(
		lists,
		/reloadLists\(\[\.\.\.MY_REQUEST_LISTS, \.\.\.TEAM_REQUEST_LISTS, myRequestCounts\], why\)/
	)
})
