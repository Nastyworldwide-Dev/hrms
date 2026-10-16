// alpha.54 (Mia, 16 Oct 2026): HomeWeek and HomeComingUp fetched on their own mount
// while sitting inside a GListPanel whose `:loading` skeleton unmounts them. A failed
// read mounted them, they fetched again, the skeleton came back and unmounted them:
// thousands of requests a second. A component placed inside a loading panel must not
// start a read when it mounts; the page that owns the panel reads once.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../../", import.meta.url))
const files = (dir) =>
	readdirSync(dir).flatMap((n) => {
		const p = join(dir, n)
		if (statSync(p).isDirectory()) return n === "__tests__" ? [] : files(p)
		return n.endsWith(".vue") ? [p] : []
	})
const byName = new Map(
	files(SRC).map((p) => [
		p
			.split("/")
			.pop()
			.replace(/\.vue$/, ""),
		p,
	])
)

//: Fetches when it mounts: an onMounted (or immediate watch) whose body starts a read.
const fetchesOnMount = (src) =>
	/onMounted\(\s*(async\s*)?\(\)\s*=>\s*\{[^}]*\.(fetch|reload|submit)\(/.test(src) ||
	/onMounted\(\s*(async\s*)?\(\)\s*=>\s*\w+\.(fetch|reload|submit)\(/.test(src) ||
	/createResource\(\{[^}]*\bauto:\s*true/.test(src)

test("nothing inside a loading panel starts a read when it mounts", () => {
	const offenders = []
	for (const [, path] of byName) {
		const src = readFileSync(path, "utf8")
		for (const panel of src.match(/<GListPanel[^>]*:loading[\s\S]*?<\/GListPanel>/g) || []) {
			for (const [, child] of panel.matchAll(/<([A-Z][A-Za-z]+)/g)) {
				const childPath = byName.get(child)
				if (!childPath || !existsSync(childPath) || child === "GListPanel") continue
				if (fetchesOnMount(readFileSync(childPath, "utf8")))
					offenders.push(`${path.slice(SRC.length)} -> ${child}`)
			}
		}
	}
	assert.deepEqual(offenders, [])
})

// The gate must still catch the case that caused it (kept honest, not a rubber stamp).
test("the rule recognises the alpha.54 shape", () => {
	assert.ok(fetchesOnMount("onMounted(() => {\n\thomeWeek.fetch()\n})"))
	assert.ok(fetchesOnMount('createResource({ url: "x", auto: true })'))
	assert.ok(!fetchesOnMount("onMounted(() => {\n\tconsole.info('hi')\n})"))
})
