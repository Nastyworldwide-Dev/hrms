// alpha.14 (owner, 27 Sep 2026: "the check-ins list, the time is
// misaligned"). Measured on the installed-iPhone profile: the time ended at
// x 263 and the chevron's box ran 275-370 — the shared row rule
// (`.g-form-row > :not(label)` = flex 1 1 0) grew the 16 pt icon into a
// 95 pt slot, so the time sat mid-row. The chevron's own rule lost on
// specificity (:not() counts its arguments). An icon in a row keeps its size;
// only text and controls share the row.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const css = readFileSync(fileURLToPath(new URL("../glass-components.css", import.meta.url)), "utf8")
const root = postcss.parse(css)

test("the row rule that shares out the width never grows an icon", () => {
	const growers = []
	root.walkRules((r) => {
		if (!r.selectors.some((s) => /^\.g-form-row > :not\(/.test(s))) return
		r.walkDecls("flex", (d) => {
			if (/^1 1 0/.test(d.value)) growers.push(...r.selectors)
		})
	})
	assert.ok(growers.length > 0, "the shared row rule is still there")
	for (const sel of growers) assert.match(sel, /:not\(svg\)/, sel)
})
