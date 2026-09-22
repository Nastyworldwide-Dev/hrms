// Three defects the owner found on a real phone, 22 Sep 2026, after deploying
// the pre-2.0 programme. Each was shipped green: every one of them is a case
// where a source-level test was satisfied and the browser did something else.
//
// 1. THE UPDATE PROMPT IS TRAPPED UNDER THE TAB BAR. It offsets itself by
//    --g-tabbar-height + 12px, which clears the bar's 64+9px by three pixels
//    — and clearing it by three pixels is not what the screenshot shows,
//    because `ion-tab-bar slot="bottom"` lives inside `ion-tabs`, inside a
//    `.relative` wrapper, inside `ion-page`. Those are STACKING CONTEXTS. A
//    z-index set in App.vue cannot rise above them whatever its value, so the
//    prompt renders behind the bar and its Reload button is half unreachable.
//    Same class as the offline bar: a fixed thing in App.vue reasoning about
//    a layout Ionic owns.
//
// 2. PULL-TO-REFRESH PRINTS THROUGH THE GREETING. `ion-refresher` is
//    `position: absolute; top: 0; z-index: -1` — deliberately BEHIND the
//    content, which works only if the content has a background. Home's does
//    not, so "Pull to refresh" shows through the date.
//
// 3. iOS STILL ZOOMS ON A SEARCH FIELD. The 16px rule is an ELEMENT selector,
//    and frappe-ui's Autocomplete renders `<ComboboxInput class="form-input">`
//    — a class beats an element on specificity, so the search box inside the
//    leave-type picker keeps its smaller size and iOS zooms the page.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")
const css = () =>
	read("theme/glass-components.css").replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))

// The selectors here carry an element or class prefix — `ion-tab-bar.g-tabbar`,
// `.ion-page.g-page` — because that is what wins against Ionic's own rules. So
// match the class at the END of a selector rather than at the start of a line.
function rule(className) {
	const text = css()
	const at = text.search(new RegExp(`\\n[^\\n{}]*\\${className} \\{`))
	return at < 0 ? null : text.slice(at, text.indexOf("}", at))
}

test("the update prompt is not trapped inside Ionic's stacking context", () => {
	// It has to be a child of the tabbed shell, where it can out-stack the tab
	// bar, OR the tab bar has to be told to sit below it. The first is a bigger
	// change; the second is one declaration and keeps the prompt in App.vue
	// where every screen gets it.
	const tabbar = rule(".g-tabbar")
	assert.ok(tabbar, ".g-tabbar should exist")
	assert.match(tabbar, /z-index:/, "the bar needs an explicit layer to sit below the prompt")
	const prompt = rule(".g-update")
	assert.match(prompt, /z-index: var\(--g-layer-scrim\)/, "and the prompt sits above it")
})

test("the update prompt clears the tab bar by more than a rounding error", () => {
	const prompt = rule(".g-update")
	// 64 + 9 is what the bar occupies; +12 left three pixels. The gap token is
	// what the bar actually uses, so the prompt must use it too rather than a
	// number somebody hoped was big enough.
	assert.match(
		prompt,
		/--g-tabbar-height\)[^;]*\+[^;]*--g-tabbar-gap/,
		"offset by the bar's own two tokens, not by a guess"
	)
})

test("the prompt can be dismissed", () => {
	// The owner could not swipe it away or clear it. A bar with one button and
	// no way out is a bar that owns the bottom of the screen for ever if the
	// reload ever fails.
	const prompt = read("components/UpdatePrompt.vue")
	assert.match(prompt, /aria-label|Dismiss|Later/, "there is a way to put it away")
})

test("pull-to-refresh cannot print through the screen it is behind", () => {
	// `ion-refresher` ships z-index:-1 — behind the page, revealed by pulling.
	// That works while the page is one flat layer, and this one is not:
	// `.g-page__content` carries z-index:1 so Ionic's content sits above the
	// light field. The refresher then lands BETWEEN the page background and
	// the content, and prints through the greeting.
	const text = css()
	const content = rule(".g-page__content")
	assert.match(
		content,
		/z-index: 1/,
		"the content's layer is what keeps the light field behind it"
	)
	const at = text.indexOf("\nion-refresher {")
	assert.ok(at > 0, "the refresher needs an explicit layer of its own")
	const refresher = text.slice(at, text.indexOf("}", at))
	const layer = Number(refresher.match(/z-index:\s*(\d+)/)?.[1])
	assert.ok(
		layer > 1,
		`the refresher must sit ABOVE the content, not between the layers (got ${layer})`
	)
})

test("a third-party input cannot bring the iOS zoom back", () => {
	// The element-level rule loses to `class="form-input"` on specificity.
	// frappe-ui renders that class inside Autocomplete, which is what the leave
	// form's type picker uses.
	const text = css()
	const at = text.indexOf("\n.form-input,")
	assert.ok(at > 0, "frappe-ui's own input class has to be named, or it keeps its smaller size")
	// ...and in the SAME rule as the floor, not merely somewhere in the file.
	assert.match(text.slice(at, text.indexOf("}", at)), /font-size: 16px/)
})
