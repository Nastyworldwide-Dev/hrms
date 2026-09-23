// A row you tap must be a control a keyboard can reach. HR's issue cards and
// the Team member rows were <div @click> — no role, no tabindex, no key
// handler — so a keyboard or switch user could not open an issue or a member
// (audit P0-12, WCAG 2.1.1 / 4.1.2). This pins the class app-wide: a <div> or
// <span> with a click handler must be a full ARIA button (role, tabindex, and
// Enter/Space), per the WAI-ARIA APG button pattern.
//
// Two shapes are not targets and are exempt: a scrim hidden from assistive tech
// (aria-hidden; Escape closes its sheet) and a capture-phase listener that only
// watches clicks (FormView's dirty tracking).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const root = fileURLToPath(new URL("../..", import.meta.url))

function vueFiles(dir) {
	return readdirSync(dir).flatMap((name) => {
		const path = join(dir, name)
		if (name === "__tests__" || name === "node_modules") return []
		if (statSync(path).isDirectory()) return vueFiles(path)
		return name.endsWith(".vue") ? [path] : []
	})
}

test("no div or span is a click target", () => {
	const offenders = []
	for (const file of [...vueFiles(join(root, "views")), ...vueFiles(join(root, "components"))]) {
		const src = readFileSync(file, "utf8")
		const template = src.slice(0, src.indexOf("<script"))
		for (const tag of template.match(/<(div|span)\b[^>]*>/g) || []) {
			if (!/\s@click(\.[a-z.]+)?=/.test(tag)) continue
			if (/aria-hidden="true"/.test(tag) || /@click\.capture=/.test(tag)) continue
			const aria =
				/role="button"/.test(tag) &&
				/tabindex="0"/.test(tag) &&
				/@keydown\.enter/.test(tag) &&
				/@keydown\.space/.test(tag)
			if (!aria) {
				offenders.push(`${file.replace(root, "")}: ${tag.slice(0, 80)}`)
			}
		}
	}
	assert.deepEqual(offenders, [])
})
