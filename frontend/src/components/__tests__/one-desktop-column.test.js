// alpha.12 desktop (measured 26 Sep 2026 at 1280): the large title sat at x=232
// while the content started at 416; inline titles were centred on the window,
// 172-340 pt off the content; five column widths (664/688/712/426/352). Pages
// disagreed — some centred their column (mx-auto), some pinned it left
// (lg:mx-0), with different side padding. Apple (layout): "Align elements to
// make them easier to scan". One rule now: at >= 1024 the bar row, the large
// title and every content column share one centred column of
// --g-content-column-lg (672, owner ruling R2).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../../", import.meta.url))
const css = readFileSync(join(SRC, "theme/glass-components.css"), "utf8")
const vueFiles = (dir) =>
	readdirSync(dir).flatMap((n) => {
		const p = join(dir, n)
		if (statSync(p).isDirectory()) return n === "__tests__" ? [] : vueFiles(p)
		return n.endsWith(".vue") ? [p] : []
	})

test("no screen pins its column to the left on desktop", () => {
	const offenders = vueFiles(SRC)
		.filter((p) => /max-w-content-column-lg[^"]*\blg:mx-0\b|\blg:mx-0\b[^"]*max-w-content-column-lg/.test(readFileSync(p, "utf8")))
		.map((p) => p.slice(SRC.length))
	assert.deepEqual(offenders, [])
})

test("one desktop rule centres the bar row and the large title on the content column", () => {
	const block = css.slice(css.indexOf("/* alpha.12: one desktop column"))
	assert.ok(block.length > 40, "the rule exists")
	const rule = block.slice(0, block.indexOf("\n}\n", block.indexOf("@media (min-width: 1024px)")) + 3)
	assert.match(rule, /@media \(min-width: 1024px\)/)
	assert.match(rule, /\.g-header[\s\S]*max-width:\s*var\(--g-content-column-lg\)/)
	assert.match(rule, /\.g-large-title[\s\S]*max-width:\s*var\(--g-content-column-lg\)/)
	assert.match(rule, /margin-inline:\s*auto/)
})
