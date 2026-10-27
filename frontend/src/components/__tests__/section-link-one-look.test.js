// Design audit, 27 Oct 2026: the section-header link (.g-seclink: "See all", "Open team roster",
// "Edit") was drawn four ways: kra-label + accent ink on Leave/Expense/Team, plain on the
// manpower review's Edit, underlined there and on the KPI breadcrumb, ink-800 on KPI's Back.
// The look lives in the class now; screens add nothing to it. KPI's Back and breadcrumb are
// navigation, not a section link, and keep the neutral ink link style (.g-backlink).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../../", import.meta.url))
const css = readFileSync(join(SRC, "theme/glass-components.css"), "utf8")
function vueFiles(dir) {
	return readdirSync(dir).flatMap((n) => {
		const p = join(dir, n)
		if (n === "__tests__" || n === "glass") return []
		return statSync(p).isDirectory() ? vueFiles(p) : n.endsWith(".vue") ? [p] : []
	})
}

test("the section link's look is in the class: link type, accent ink", () => {
	const rule = css.match(/\n\.g-seclink \{[^}]*\}/)?.[0] ?? ""
	assert.match(rule, /font-size: var\(--g-type-kra-label-size\)/)
	assert.match(rule, /color: rgb\(var\(--g-accent-ink-rgb\)\)/)
})

test("no screen restyles a section link", () => {
	for (const file of [...vueFiles(join(SRC, "views")), ...vueFiles(join(SRC, "components"))]) {
		for (const m of readFileSync(file, "utf8").matchAll(/class="([^"]*\bg-seclink\b[^"]*)"/g)) {
			const extra = m[1].split(/\s+/).filter((c) => c && !["g-seclink", "g-focusable", "self-start", "flex-none"].includes(c))
			assert.deepEqual(extra, [], `${file.replace(SRC, "")}: ${m[1]}`)
		}
	}
})
