// alpha.8 (owner's iPhone, 25 Sep): the announcement preview ran to three
// lines under its title. iOS Mail shows two, then an ellipsis; a subtitle in
// a list row never grows past that.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import postcss from "postcss"

const root = postcss.parse(readFileSync(fileURLToPath(new URL("../../theme/glass-components.css", import.meta.url)), "utf8"))
test("a row's subtitle stops at two lines", () => {
	const out = {}
	root.walkRules((r) => {
		if (r.parent.type === "root" && r.selectors.includes(".g-row__sub")) r.walkDecls((d) => (out[d.prop] = d.value))
	})
	assert.equal(out["-webkit-line-clamp"], "2")
	assert.equal(out.overflow, "hidden")
})
