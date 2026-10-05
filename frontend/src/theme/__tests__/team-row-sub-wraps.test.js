// The Team row's second line carries the facts a boss reads: "IN 12:38 · OUT — · Half day". On one
// line (nowrap + ellipsis) a 360px phone cut the LAST words off first, and the last words are the
// ones that say the day was a half (design review of ff899b5a4, 5 Oct 2026). Two lines, like every
// other row's sublabel.
import assert from "node:assert"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import test from "node:test"

const CSS = fs.readFileSync(
	path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "glass-components.css"),
	"utf8"
)

// the block that styles .g-team-row__sub on its own (not the shared font-size one)
const block = CSS.match(/\.g-team-row__sub\s*\{[^}]*-webkit-line-clamp[^}]*\}|\.g-team-row__sub\s*\{[^}]*white-space[^}]*\}/)?.[0] ?? ""

test("the team row's second line may use two lines", () => {
	assert.match(block, /-webkit-line-clamp:\s*2/)
})

test("the team row's second line is not forced onto one line", () => {
	assert.doesNotMatch(block, /white-space:\s*nowrap/)
})
