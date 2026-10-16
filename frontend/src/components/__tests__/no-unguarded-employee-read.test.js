// alpha.55 (Mia, 16 Oct 2026): a login with no Employee record reaches Nadi
// (navigationGate lets "employee unknown" through, so viewer-only screens keep
// working), and CheckInPanel crashed in setup reading `employee.data.name`:
// "Cannot read properties of undefined (reading 'name')". Every read is guarded,
// so the request reaches the server, whose refusal says in plain words that the
// account is not linked to an employee record.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../../", import.meta.url))
const files = (dir) =>
	readdirSync(dir).flatMap((n) => {
		const p = join(dir, n)
		if (statSync(p).isDirectory()) return n === "__tests__" ? [] : files(p)
		return /\.(vue|js)$/.test(n) ? [p] : []
	})

test("no screen reads employee.data.<field> without a guard", () => {
	const offenders = files(SRC).flatMap((p) =>
		readFileSync(p, "utf8")
			.split("\n")
			.map((line, i) => [line, i + 1])
			// comments may name the old shape; only code is checked
			.filter(([line]) => !/^\s*(\/\/|\*|<!--)/.test(line))
			.filter(([line]) => /\bemployee\.data\.[a-z_]/.test(line))
			.map(([, n]) => `${p.slice(SRC.length)}:${n}`)
	)
	assert.deepEqual(offenders, [])
})
