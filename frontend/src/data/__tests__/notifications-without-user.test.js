// alpha.14 (states audit, 27 Sep 2026): with the server failing, pages hung
// on the launch placeholder 1 run in 3–4. data/notifications.js built its list
// filter from `userResource.data.name` when the module loaded (the header
// imports it on every page); when that read had failed, data was null, the
// import threw, and the page never mounted. The session user comes from the
// cookie (personalCache.sessionUser), which exists without any server read.
// The server fences PWA Notification to its to_user either way
// (pwa_notification.get_permission_query_conditions).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../notifications.js", import.meta.url)), "utf8")

test("the notification list never reads userResource.data while the module loads", () => {
	assert.doesNotMatch(src, /userResource\.data\.name/)
	assert.match(src, /filters: \{ to_user: sessionUser\(\) \}/)
})

// The class: nothing in src/data reads a resource's .data.<field> without
// `?.` — a data module is imported by pages that render while that read has
// failed or not landed.
test("no data module reads resource.data.<field> unguarded", async () => {
	const { readdirSync } = await import("node:fs")
	const dir = fileURLToPath(new URL("..", import.meta.url))
	const bad = []
	for (const f of readdirSync(dir).filter((n) => n.endsWith(".js"))) {
		const text = readFileSync(`${dir}/${f}`, "utf8").split("\n")
		text.forEach((line, i) => {
			if (/^\s*\/\//.test(line)) return
			if (/(Resource|resource)\.data\.[a-z_]+/.test(line)) bad.push(`${f}:${i + 1} ${line.trim()}`)
		})
	}
	assert.deepEqual(bad, [])
})
