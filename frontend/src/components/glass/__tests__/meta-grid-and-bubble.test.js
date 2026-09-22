// Two hand-built surfaces became primitives (revamp slice A2/A3, spec §15.2).
//
// TicketDetail held `.g-glass` twice: once on a hand-rolled 2-up meta grid
// with its own dividers and padding, once on the "them" side of every chat
// bubble. Views are not allowed to hold that class — the usage gate says so —
// and the reason is not bureaucratic: a surface built inline keeps its own
// copy of the radius, the padding and the divider colour, so when the system
// moves (as it did on 22 Sep, when every spacing value went to a 4pt grid)
// the hand-built one stays where it was and the screen quietly drifts.
//
// What is asserted here is the boundary, not the markup: the CONTAINER owns
// the glass, the cells do not, and the view no longer names the class at all.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")

function code(text) {
	return text
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))
}

//: The same expression the usage gate counts with. A bare /g-glass/ also
//: matches inside --g-glass-fill, which a component is entitled to use.
const GLASS = /(?<!-)\bg-glass(?:-ghost)?\b(?!-)/g

test("the ticket screen no longer builds its own surfaces", () => {
	const view = code(read("views/helpdesk/TicketDetail.vue"))
	assert.deepEqual(view.match(GLASS), null, "a view may not carry the surface class")
	assert.match(view, /<GMetaGrid/, "the facts are a primitive")
	assert.match(view, /<GChatBubble/, "and so is a message")
})

test("GMetaGrid is one surface, and its cells are cells", () => {
	const c = code(read("components/glass/GMetaGrid.vue"))
	assert.equal((c.match(GLASS) || []).length, 1, "exactly one glass element")
	// The cell loop must not sit on the glass element itself — that would make
	// N cells N surfaces and spend a whole screen's §15 budget on four words.
	const cellRow = c.split("\n").find((l) => l.includes('v-for="cell in cells"'))
	assert.ok(cellRow, "the cells are a loop")
	assert.doesNotMatch(cellRow, GLASS, "a cell is not a surface")
})

test("GMetaGrid does not hardcode what the token system owns", () => {
	// The whole reason this exists. The hand-built version carried px-3.5,
	// py-3, border-r and border-b; none of those move when the grid does.
	const c = code(read("components/glass/GMetaGrid.vue"))
	assert.doesNotMatch(c, /\bp[xy]?-\d/, "padding comes from the cell class")
	assert.doesNotMatch(c, /\bborder-[rbtl]\b/, "dividers are drawn by the grid, once")
	const css = code(read("theme/glass-components.css"))
	assert.match(css, /\.g-cellgrid--meta/, "the grid is in the system's stylesheet")
	assert.match(css, /--g-hair/, "and its dividers use the hair token")
})

test("a thread costs one surface, not one per message", () => {
	// The inline version put .g-glass on the "them" bubble under a v-for, so a
	// twenty-message thread was twenty blurred surfaces against a budget of
	// six — and blur is the expensive thing on a mid-range Android (§15). It
	// hid in a view, where the surfaces gate counts markup instead of resolving
	// components; moving it into a primitive is what let the gate see it.
	const c = code(read("components/glass/GChatBubble.vue"))
	assert.deepEqual(c.match(GLASS), null, "§15.2: a repeated surface is flattened, not glassed")
})

test("the two bubble sides are told apart by more than a name", () => {
	// A thread where both sides look alike has to be read; a thread where they
	// differ can be skimmed. `mine` is the only input that decides it.
	const c = code(read("components/glass/GChatBubble.vue"))
	assert.match(c, /mine \? 'g-bubble--mine' : 'g-bubble--theirs'/, "one prop decides the side")
	const css = code(read("theme/glass-components.css"))
	assert.match(
		css,
		/\.g-bubble--mine[\s\S]*?border-bottom-right-radius/,
		"the reader's tail points right"
	)
	assert.match(
		css,
		/\.g-bubble--theirs[\s\S]*?border-bottom-left-radius/,
		"and theirs points left"
	)
	// Both sides are solid. A fill that differs is what carries the distinction
	// once the blur is gone.
	const mine = css.slice(css.indexOf(".g-bubble--mine"), css.indexOf(".g-bubble--theirs"))
	const theirs = css.slice(css.indexOf(".g-bubble--theirs"), css.indexOf(".g-bubble__who"))
	assert.match(mine, /background:/, "the reader's side has its own fill")
	assert.match(theirs, /background:/, "and so does the other")
	assert.notEqual(
		mine.match(/background:[^;]+;/)?.[0],
		theirs.match(/background:[^;]+;/)?.[0],
		"two sides, two fills"
	)
})

test("the bubble takes its sizes from tokens, not from numbers", () => {
	const css = code(read("theme/glass-components.css"))
	const block = css.slice(css.indexOf("\n.g-bubble {"), css.indexOf("\n.g-bubble__body"))
	// A raw px font-size or radius here is exactly the drift this slice removes.
	assert.doesNotMatch(block, /font-size:\s*\d/, "type size is a token")
	assert.doesNotMatch(block, /border-radius:\s*\d/, "radius is a token")
	assert.match(block, /var\(--g-type-row-label-size\)/, "and it is the ramp's body step")
})
