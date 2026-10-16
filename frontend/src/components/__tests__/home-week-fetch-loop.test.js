// Mia, 16 Oct 2026: a login with no Employee record left Nadi open and the console
// grew thousands of lines a second. HomeWeek and HomeComingUp fetched on their own
// mount, but they sit inside the GListPanel whose skeleton (homeWeek.loading)
// unmounts them: a failed read mounted them, they refetched, the skeleton came back
// and unmounted them, the read failed, and so on forever. Home fetches them once.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("the cards inside the loading panel never fetch on their own mount", () => {
	assert.doesNotMatch(read("../HomeWeek.vue"), /homeWeek\.(fetch|reload)\(/)
	assert.doesNotMatch(read("../HomeComingUp.vue"), /homeComingUp\.(fetch|reload)\(/)
})

test("Home fetches both once when it mounts", () => {
	const src = read("../../views/Home.vue")
	assert.match(src, /onMounted\(\(\) => \{\s*homeWeek\.fetch\(\)\s*homeComingUp\.fetch\(\)\s*\}\)/)
})
