// Sentence case for every interface label (audit F-8 / APP-22; GOV.UK style,
// Material 3 writing, BDA dyslexia style guide). 76+ labels were Title Case
// ("Change Password", "Log Out"), and one thing had two names ("Change
// password" on You, "Change Password" in Settings). A label here is a short
// __() string with no sentence punctuation; proper names and acronyms are kept.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const root = fileURLToPath(new URL("..", import.meta.url))
const KEEP =
	/\{|\bHR\b|\bIT\b|\bOT\b|SOPs?\b|KPIs?\b|KRAs?\b|PDF|PWA|CEO|\bRM\b|Nadi|Frappe|ERPNext|Desk\b|Approva|Google|Microsoft|Bahasa|English|Malaysia|\bNew\b|Home\b|Settings\b|Requests\b|Calendar\b|Score\b|More\b|You\b/

function files(dir) {
	return readdirSync(dir).flatMap((name) => {
		const path = join(dir, name)
		if (name === "__tests__") return []
		if (statSync(path).isDirectory()) return files(path)
		return /\.(vue|js)$/.test(name) ? [path] : []
	})
}

test("interface labels are sentence case", () => {
	const offenders = []
	for (const file of files(root)) {
		// Comments are not interface text (they quote status values like "Not In Yet").
		const code = readFileSync(file, "utf8").replace(/\/\/[^\n]*/g, "")
		for (const match of code.matchAll(/__\(\s*(["'])(.+?)\1/g)) {
			const text = match[2]
			if (/[.!?:]\s/.test(text) || text.endsWith(".") || KEEP.test(text)) continue
			const words = text.match(/[A-Za-z][A-Za-z'’]*/g) || []
			if (words.length < 2) continue
			if (words.slice(1).some((w) => /^[A-Z][a-z]/.test(w)))
				offenders.push(`${file.replace(root, "")}: ${text}`)
		}
	}
	assert.deepEqual(offenders, [])
})
