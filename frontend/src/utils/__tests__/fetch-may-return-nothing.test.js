// frappe-ui's resource.fetch() returns undefined when it skips a request
// (already loading, or served from cache), so `.fetch().catch(...)` throws a
// TypeError instead of catching one. Live audit 23 Sep: Help threw on every
// open. This guards the whole app against the pattern.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const walk = (dir) =>
	readdirSync(dir).flatMap((name) => {
		const path = join(dir, name)
		if (statSync(path).isDirectory()) return name === "__tests__" ? [] : walk(path)
		return /\.(vue|js)$/.test(name) ? [path] : []
	})

test("no .fetch()/.reload()/.submit() .catch() without optional chaining", () => {
	const offenders = walk(SRC).filter((file) =>
		/\.(fetch|reload|submit)\(\)\s*\.catch\(/.test(readFileSync(file, "utf8"))
	)
	assert.deepEqual(offenders, [])
})
