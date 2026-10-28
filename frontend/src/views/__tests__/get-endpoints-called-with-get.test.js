import assert from "node:assert/strict"
import { test } from "node:test"
import { readdirSync, readFileSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const API = fileURLToPath(new URL("../../../../hrms/api", import.meta.url))
const SRC = fileURLToPath(new URL("../..", import.meta.url))

// Pre-existing offenders, tracked in .claude/plans/ticket-get-endpoints-post.md
const KNOWN = new Set([])

function walk(dir) {
	return readdirSync(dir).flatMap((f) => {
		const p = join(dir, f)
		if (statSync(p).isDirectory()) return f === "__tests__" || f === "node_modules" ? [] : walk(p)
		return /\.(vue|js)$/.test(f) ? [p] : []
	})
}

test("every GET-only endpoint is called with method GET", () => {
	const getOnly = new Set()
	for (const f of readdirSync(API).filter((n) => n.endsWith(".py"))) {
		const src = readFileSync(join(API, f), "utf8")
		for (const m of src.matchAll(/@frappe\.whitelist\(methods=\["GET"\]\)\s*\ndef (\w+)\(/g)) {
			getOnly.add(`hrms.api.${f.slice(0, -3)}.${m[1]}`)
		}
	}
	assert.ok(getOnly.size > 0, "should find GET-only endpoints")
	const bad = []
	for (const file of walk(SRC)) {
		const src = readFileSync(file, "utf8")
		for (const m of src.matchAll(/url:\s*"(hrms\.api\.\w+\.\w+)"/g)) {
			if (!getOnly.has(m[1])) continue
			const start = src.lastIndexOf("createResource(", m.index)
			const end = src.indexOf("\n\t})", m.index)
			const block = src.slice(start < 0 ? m.index : start, end < 0 ? undefined : end)
			if (!/method:\s*"GET"/.test(block) && !KNOWN.has(file.slice(SRC.length)))
				bad.push(`${file.slice(SRC.length)} -> ${m[1]}`)
		}
	}
	assert.deepEqual(bad, [])
})
