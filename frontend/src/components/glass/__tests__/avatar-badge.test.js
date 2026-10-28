// GAvatar's `badge` mode (owner, 28 Oct 2026): two letters on a black disc
// with a lime ring, the same in light and dark. Opt-in, so the header and
// Profile keep their one-letter grey avatar.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const src = readFileSync(new URL("../GAvatar.vue", import.meta.url), "utf8")
const css = readFileSync(new URL("../../../theme/glass-components.css", import.meta.url), "utf8")
const rule = (sel) => css.match(new RegExp(`${sel.replace(/[.-]/g, "\\$&")}\\s*\\{([^}]*)\\}`))?.[1] || ""

test("GAvatar has an opt-in badge prop that uses the shared initials helper", () => {
	assert.match(src, /badge:\s*\{\s*type:\s*Boolean,\s*default:\s*false\s*\}/)
	assert.match(src, /import \{ initials \} from "@\/utils\/avatar"/)
	assert.match(src, /props\.badge \? initials\(props\.label\)/)
	assert.match(src, /'g-avatar--badge': badge/)
})

test("the badge is a black disc, white letters and a lime ring, from tokens only", () => {
	const r = rule(".g-avatar--badge")
	assert.match(r, /background:\s*var\(--g-person-badge\)/)
	assert.match(r, /color:\s*var\(--g-on-person-badge\)/)
	// outline, not an inset box-shadow: a photo (<img>) paints over an inset
	// shadow, so the ring vanished for anyone with a picture
	assert.match(r, /outline:\s*var\(--g-avatar-ring, 2px\) solid var\(--g-brand\)/)
	assert.match(r, /outline-offset:\s*calc\(var\(--g-avatar-ring, 2px\) \* -1\)/)
	assert.doesNotMatch(r, /box-shadow/)
	assert.doesNotMatch(r, /#[0-9a-f]{3,8}\b|rgb\(/i)
})

test("the badge does not change in dark mode", () => {
	assert.doesNotMatch(css, /data-theme="dark"\]\s*\.g-avatar--badge/)
})

test("badge letters never drop below 11px, the smallest size in the type scale", () => {
	assert.match(src, /Math\.max\(11, Math\.round\(props\.size \* 0\.36\)\)/)
})
