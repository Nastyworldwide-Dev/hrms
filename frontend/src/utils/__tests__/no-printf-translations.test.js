import assert from "node:assert/strict"
import { test } from "node:test"
import { readdirSync, readFileSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))

function walk(dir) {
	return readdirSync(dir).flatMap((f) => {
		const p = join(dir, f)
		if (statSync(p).isDirectory()) return f === "__tests__" || f === "node_modules" ? [] : walk(p)
		return /\.(vue|js)$/.test(f) ? [p] : []
	})
}

test("translated strings use {0}, never printf %s (the plugin only fills {n})", () => {
	const hits = []
	for (const file of walk(SRC)) {
		const src = readFileSync(file, "utf8")
		for (const m of src.matchAll(/__\(\s*(["'])(?:(?!\1).)*%s(?:(?!\1).)*\1/g))
			hits.push(`${file.slice(SRC.length)}: ${m[0]}`)
	}
	assert.deepEqual(hits, [])
})
