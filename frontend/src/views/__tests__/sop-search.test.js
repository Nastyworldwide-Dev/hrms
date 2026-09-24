// An SOP library is a lookup tool, not a browse tool (revamp §7, slice D3).
//
// Somebody opening it is usually after one document they half remember, so
// search comes first. Three things were wrong with the search it had, and
// none of them is visible in a screenshot:
//
//   it re-filtered and re-grouped the whole library on every keystroke, so
//   the list flickered through nonsense between letters;
//   it had no way to clear;
//   it was a hand-built <input> beside a system component that already does
//   all of this — which is how this one screen came to hold 20 of the app's
//   103 stray pixel values.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")

const code = (text) =>
	text
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))

const view = code(read("views/sop/SopList.vue"))

test("the search bar is the system's, not this screen's own", () => {
	assert.match(view, /<GSearchBar/)
	// The hand-built one carried its own border, padding and icon placement,
	// and drifted from every other search in the app because nothing tied it
	// to them.
	assert.doesNotMatch(view, /<input\s+v-model="typed"/, "no hand-built input")
	assert.doesNotMatch(view, /placeholder:text-ink-500/, "nor its own placeholder styling")
})

test("typing and filtering are two different values", () => {
	// Without the split there is nothing to debounce: the list is whatever the
	// last keystroke said, re-grouped between letters.
	assert.match(view, /const typed = ref\(""\)/)
	assert.match(view, /const query = ref\(""\)/)
	assert.match(
		view,
		/buildSopSections\(sops\.data, query\.value\)/,
		"the list reads the settled one"
	)
	assert.match(view, /v-model="typed"/, "and the field writes the other")
})

test("the debounce is a named threshold, not a magic number", () => {
	// 300ms is Nielsen's perceptual limit. A number with no name is a number
	// somebody tunes to 50 and breaks the thing it was for.
	assert.match(view, /const SEARCH_DEBOUNCE_MS = 300/)
	assert.match(view, /setTimeout\(\s*\(\) => \{[\s\S]{0,80}query\.value = value/)
})

test("clearing is instant", () => {
	// Somebody who taps the × wants the full list back now. Waiting 300ms to
	// show them what they already had reads as lag, not as smoothing.
	// Sliced to the CLEANUP CALL, not to "onBeforeUnmount" — that string
	// appears in the import line ABOVE the watcher, so slicing to it produced
	// an empty string and the assertion below passed on nothing.
	const watcher = view.slice(view.indexOf("watch(typed"), view.indexOf("onBeforeUnmount(() =>"))
	assert.ok(watcher.length > 0, "the watcher was actually found")
	// Comments are BLANKED rather than removed by `code`, so the gap between
	// the guard and the assignment is however many lines of explanation sit
	// there. Matched without a width bound for that reason — the first version
	// of this used {0,60} and failed on a three-line comment.
	assert.match(watcher, /if \(!value\) \{[\s\S]*?query\.value = ""/)
	assert.match(view, /@clear="typed = ''"/, "and the bar offers the control")
})

test("the timer is cleaned up", () => {
	// A pending timeout on an unmounted component writes to a ref nobody is
	// rendering — §15 of the checklist: clean up listeners, timers, observers.
	assert.match(view, /onBeforeUnmount\(\(\) => clearTimeout\(debounce\)\)/)
	assert.match(
		view,
		/clearTimeout\(debounce\)\s*\n\s*\/\/|clearTimeout\(debounce\)/,
		"and reset between keystrokes"
	)
})

test("no results and nothing yet stay two different states", () => {
	// Conflating them is why an empty search box reads as a broken app. This
	// screen already had it right; the assertion keeps it that way.
	assert.match(view, /No SOPs match/, "a search that found nothing")
	assert.match(view, /No SOPs yet/, "a library with nothing in it (alpha.6: plain word, was \"documents\")")
	assert.match(view, /v-else-if="query"/, "and the search state is checked first")
})
