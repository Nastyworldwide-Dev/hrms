// The app has never been checked at 320px (revamp slice A12, §27).
//
// No support matrix existed, so "does it work" had no answer. 320px is the
// floor because it is the narrowest device still in use (iPhone SE 1st gen,
// and any phone at 200% text zoom reflows to about that) and because WCAG 2.1
// SC 1.4.10 (Reflow) requires content to work at 320 CSS px without
// two-dimensional scrolling.
//
// This is a STATIC check, not a render: it walks the layout declarations that
// can produce horizontal overflow and refuses the shapes that do. A rendering
// test needs a served site, which the visual and a11y gates already wait for;
// this one runs on any laptop, which is what makes it a gate rather than an
// aspiration.
//
// What produces overflow at 320:
//   a fixed width at or above the floor minus the gutters
//   a min-width that cannot shrink
//   a grid template with fixed columns summing past the content width
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join, relative } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../src", import.meta.url))
const tokens = JSON.parse(
	readFileSync(
		fileURLToPath(new URL("../../design/tokens.json", import.meta.url)),
		"utf8"
	)
)

//: The narrowest supported viewport. Read from the token rather than written
//: here, so the number lives in one place and a layout decision has something
//: to be measured against.
const FLOOR = parseInt(tokens.layout["viewport-floor"].value, 10)
//: Both gutters. Content lives inside them, so that is what a fixed width
//: actually has to fit into.
const GUTTER = parseInt(tokens.spacing["screen-gutter"].value, 10)
const CONTENT = FLOOR - GUTTER * 2

const decomment = (text) =>
	text
		.split(/(\/\*[\s\S]*?\*\/)/)
		.filter((p) => !p.startsWith("/*"))
		.join("")
		.split(/(<!--[\s\S]*?-->)/)
		.filter((p) => !p.startsWith("<!--"))
		.join("")

function walk(dir, out = []) {
	for (const entry of readdirSync(dir)) {
		const path = join(dir, entry)
		if (statSync(path).isDirectory()) {
			if (entry !== "__tests__") walk(path, out)
		} else if (/\.(vue|css)$/.test(entry)) out.push(path)
	}
	return out
}

const FILES = walk(SRC).filter(
	(f) => !/theme\/glass\.(css|variables\.css)$/.test(f)
)

test("the floor is a stated number, not a habit", () => {
	// WCAG 1.4.10 is what sets it, and the token says so — a number with no
	// reason attached is the thing that gets "adjusted" later.
	assert.equal(FLOOR, 320)
	assert.match(
		tokens.layout["viewport-floor"].description,
		/1\.4\.10|Reflow/,
		"the criterion is named"
	)
	assert.ok(
		GUTTER > 0 && GUTTER % 4 === 0,
		"the gutter is a real, on-grid token"
	)
	assert.ok(CONTENT > 0)
})

test("nothing is wider than the content column at the floor", () => {
	// A fixed width past this scrolls the PAGE sideways, which is the failure
	// 1.4.10 names: content that needs scrolling in two dimensions at once.
	const offenders = []
	for (const file of FILES) {
		const text = decomment(readFileSync(file, "utf8"))
		for (const m of text.matchAll(/(?<![-\w])width:\s*(\d+)px/g)) {
			if (Number(m[1]) > CONTENT)
				offenders.push(`${relative(SRC, file)}: width: ${m[1]}px`)
		}
		// Tailwind's arbitrary width, same rule.
		for (const m of text.matchAll(/\bw-\[(\d+)px\]/g)) {
			if (Number(m[1]) > CONTENT)
				offenders.push(`${relative(SRC, file)}: w-[${m[1]}px]`)
		}
	}
	assert.deepEqual(
		offenders,
		[],
		`nothing may exceed ${CONTENT}px (${FLOOR} minus two ${GUTTER}px gutters)`
	)
})

test("a min-width never pins something wider than the screen", () => {
	// min-width is worse than width: it refuses to shrink, so it overflows
	// even inside a flex parent that would otherwise cope.
	const offenders = []
	for (const file of FILES) {
		const text = decomment(readFileSync(file, "utf8"))
		// `@media (min-width: 1024px)` is a BREAKPOINT, not a box: it is the
		// mechanism by which a layout adapts, so counting it as an overflow
		// risk would fail the app for being responsive. The first version of
		// this test did exactly that and reported three false positives.
		for (const m of text.matchAll(/(^|[^(])\bmin-width:\s*(\d+)px/gm)) {
			if (Number(m[2]) > CONTENT)
				offenders.push(`${relative(SRC, file)}: min-width: ${m[2]}px`)
		}
		for (const m of text.matchAll(/\bmin-w-\[(\d+)(px|rem)\]/g)) {
			const px = m[2] === "rem" ? Number(m[1]) * 16 : Number(m[1])
			if (px > CONTENT)
				offenders.push(`${relative(SRC, file)}: min-w-[${m[1]}${m[2]}]`)
		}
	}
	assert.deepEqual(
		offenders,
		[],
		"a min-width above the content column cannot reflow"
	)
})

test("a fixed grid template fits, or it is not fixed", () => {
	// grid-cols-[110px_1fr] is fine; grid-cols-[280px_1fr] is a sideways
	// scrollbar on an SE. Only the FIXED tracks are summed — fr and auto
	// shrink by definition.
	const offenders = []
	for (const file of FILES) {
		const text = decomment(readFileSync(file, "utf8"))
		for (const m of text.matchAll(/grid-cols-\[([^\]]+)\]/g)) {
			const fixed = [...m[1].matchAll(/(\d+)px/g)].reduce(
				(sum, n) => sum + Number(n[1]),
				0
			)
			if (fixed > CONTENT)
				offenders.push(
					`${relative(SRC, file)}: grid-cols-[${m[1]}] = ${fixed}px fixed`
				)
		}
	}
	assert.deepEqual(
		offenders,
		[],
		"fixed tracks must fit inside the content column"
	)
})

test("the desktop column is a max, never a min", () => {
	// 720px as a width would overflow every phone in existence. It is applied
	// as max-w-* and must stay that way; this is the one place where getting
	// the property wrong breaks the narrow case completely.
	const column = tokens.layout["content-column-lg"].value
	assert.match(column, /^\d+px$/)
	const offenders = []
	for (const file of FILES) {
		const text = decomment(readFileSync(file, "utf8"))
		// `max-w-content-column-lg` CONTAINS `w-content-column-lg`, so a bare
		// match flagged every correct usage in the app. What is being refused
		// is the utility used WITHOUT the max- prefix.
		for (const m of text.matchAll(
			/(^|[^-\w])((?:min-)?w)-content-column(?:-lg|-read)?\b/g
		)) {
			offenders.push(`${relative(SRC, file)}: ${m[2]}-content-column…`)
		}
	}
	assert.deepEqual(
		offenders,
		[],
		"use max-w-content-column-*; w- and min-w- overflow a phone"
	)
})
