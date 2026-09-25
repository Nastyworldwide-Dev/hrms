// Invariant (A-C1, 21 Sep 2026): every resource keyed `hrms:my_*` under
// src/data is reloaded by at least one NON-socket path. The socket is a
// bonus; mount, pull-to-refresh, reconnect and long-hidden resume are the
// guarantee, and all four go through data/requestLists.js.
// Run: cd frontend && node --experimental-test-module-mocks --test tests/audit/request-lists-reload.test.mjs
import test from "node:test"
import assert from "node:assert/strict"
import { join } from "node:path"

import { SRC, read, sourceFiles } from "./_lib.mjs"

const registry = read(join(SRC, "data", "requestLists.js"))
const panel = read(join(SRC, "components", "RequestPanel.vue"))
// The lists live on Requests since the Home plan (1cdd9ff56); its pull reloads them.
const home = read(join(SRC, "views", "Requests.vue"))

function cachedResources(prefix) {
	const found = []
	for (const file of sourceFiles(join(SRC, "data"))) {
		const source = read(file)
		for (const match of source.matchAll(
			/cache: personalCacheKey\("([^"]+)"\)/g
		)) {
			if (!match[1].startsWith(prefix)) continue
			const before = source.slice(0, match.index)
			const owner = [
				...before.matchAll(/export const (\w+) = create(?:List)?Resource\(/g),
			].pop()
			found.push(owner[1])
		}
	}
	return found
}

test("every hrms:my_* resource is in the reload registry", () => {
	const mine = cachedResources("hrms:my_")
	assert.ok(mine.length >= 6, `expected the six Home lists, found ${mine}`)
	for (const name of mine) {
		assert.match(
			registry,
			new RegExp(`my: ${name}\\b`),
			`${name} missing from REQUEST_LISTS`
		)
	}
})

test("every hrms:team_* status list is in the reload registry", () => {
	for (const name of cachedResources("hrms:team_")) {
		if (name === "teamManagers") continue // not a request list
		assert.match(
			registry,
			new RegExp(`\\b${name}\\b`),
			`${name} missing from REQUEST_LISTS`
		)
	}
})

test("the registry is reached from mount, pull-to-refresh, reconnect and resume", () => {
	const mounted = panel.slice(panel.indexOf("onMounted("))
	assert.match(
		mounted,
		/reloadRequestLists\("mount"\)/,
		"RequestPanel reloads on mount"
	)
	assert.match(
		mounted,
		/useReloadOnGap\(reloadRequestLists\)/,
		"reconnect + long-hidden resume"
	)
	assert.match(
		mounted,
		/reloadLists\(\[lists\.my, \.\.\.lists\.team\]/,
		"list_update reloads my* too"
	)
	assert.match(
		home,
		/<GPullRefresh @refresh="refreshRequests"/,
		"Requests has pull-to-refresh"
	)
	assert.match(home, /await reloadRequestLists\("pull"\)/)
})

test("a cached paint says it is refreshing until the first fetch answers", () => {
	// Said to screen readers, not drawn: the visible line pushed the list down
	// 33 pt on every visit and pulled it back (alpha.8 r3, measured).
	assert.match(panel, /class="sr-only" role="status">\{\{ refreshing \? __\("Refreshing…"\)/)
	assert.match(panel, /!list\.fetched && !list\.error/)
})

test("the panel sorts on site time, never on `new Date(creation)` (Safari Invalid Date)", () => {
	assert.doesNotMatch(panel, /new Date\(/)
	assert.match(
		panel,
		/siteTime\(b\.creation\)\.valueOf\(\) - siteTime\(a\.creation\)\.valueOf\(\)/
	)
})
