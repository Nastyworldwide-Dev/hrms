// alpha.7 Phase 1 (plan §5.2, review A3): iOS shows a status as COLOURED
// TEXT in the system colours (Mail, Wallet, Settings), not a filled pill.
// Colours: Apple iOS 26 dark green #30D158 / orange #FF9230 / red #FF4245;
// light uses the accessible (increased-contrast) variants so text clears
// 4.5:1 on both the page (#F2F2F7) and the cell (#FFFFFF).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const tokens = JSON.parse(read("../../../../../design/tokens.json"))["color-semantic"]

test("status inks are Apple's colours", () => {
	assert.deepEqual(tokens["success-ink"].value, { light: "#1F7A36", dark: "#30D158" })
	assert.deepEqual(tokens["warn-ink"].value, { light: "#B24A00", dark: "#FF9230" })
	assert.deepEqual(tokens["danger-ink"].value, { light: "#D70015", dark: "#FF4245" })
})

test("a status chip is text: no fill, no outline, no padding box", () => {
	const root = postcss.parse(read("../../../theme/glass-components.css"))
	for (const v of ["neutral", "progress", "success", "danger", "muted", "attention"]) {
		const decls = {}
		root.walkRules((r) => {
			if (r.parent.type === "root" && r.selectors.includes(`.g-chip--${v}`))
				r.walkDecls((d) => (decls[d.prop] = d.value))
		})
		assert.ok(decls.color, `.g-chip--${v} sets a colour`)
		assert.ok(!decls.background || decls.background === "transparent", `${v} background ${decls.background}`)
		assert.ok(!decls.border, `${v} border ${decls.border}`)
	}
})
