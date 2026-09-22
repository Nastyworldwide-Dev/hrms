// Two things the app never told the employee (pre-2.0 R3, checklist §3 §6 §12).
//
// OFFLINE. `navigator.onLine` appears nowhere in src/. The offline banner
// exists — GBanner renders it in the design specimen — and nothing has ever
// triggered it. So a phone that loses signal mid-shift looks exactly like a
// phone whose server is slow: taps do nothing, a spinner sits there, and the
// employee tries again. The checklist's rule is that empty must be
// distinguishable from failed; unreachable is the same rule one layer down.
//
// UPDATES. `registerType: "autoUpdate"` plus `self.skipWaiting()` means a new
// build takes over the moment it finishes downloading — mid-session, mid-form.
// The employee is typing a leave reason and the page reloads under them. The
// checklist asks that update behaviour be CONTROLLED; taking over silently is
// the opposite, and it is worse here than on a content site because the thing
// being interrupted is a half-written request.
//
// Both are pinned as BEHAVIOUR, not as a particular component: the app knows
// it is offline and says so, and a waiting update asks before it takes the
// page.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")

function walk(dir, out = []) {
	for (const entry of readdirSync(dir)) {
		const path = join(dir, entry)
		if (statSync(path).isDirectory()) walk(path, out)
		else if (/\.(vue|js)$/.test(entry) && !path.includes("__tests__")) out.push(path)
	}
	return out
}

test("the app knows when it is offline", () => {
	const files = walk(SRC).map((p) => readFileSync(p, "utf8"))
	assert.ok(
		files.some((text) => /navigator\.onLine/.test(text)),
		"nothing reads the browser's own connectivity"
	)
	assert.ok(
		files.some((text) => /addEventListener\(\s*["']offline["']/.test(text)),
		"and nothing listens for the moment it changes"
	)
})

test("being offline is one fact, read from one place", () => {
	// Three screens each polling navigator.onLine would be three answers that
	// can disagree, which is exactly what the checklist's state-management rule
	// forbids. A composable, imported.
	const composable = read("composables/useOnline.js")
	assert.match(composable, /navigator\.onLine/)
	assert.match(composable, /addEventListener\(\s*["']online["']/)
	assert.match(composable, /addEventListener\(\s*["']offline["']/)
	// Not a bare mention: `void 0 && window.removeEventListener(...)` contains
	// the word and removes nothing — it survived this assertion as a mutant.
	// Pin the DISPOSAL: the pair the per-component helper adds must both come
	// off in its scope-dispose hook.
	const dispose = composable.slice(composable.indexOf("onScopeDispose"))
	// Anchored to the START of its line. A source-level test cannot see
	// reachability, so what it CAN pin is the shape: an unconditional
	// statement, not an expression guarded by something that is always false.
	// `void 0 && window.removeEventListener(...)` survived the unanchored
	// version, because the call text was still there.
	assert.match(dispose, /^\t*window\.removeEventListener\("online", up\)$/m)
	assert.match(dispose, /^\t*window\.removeEventListener\("offline", down\)$/m)
	// ...and the SHARED pair is deliberately permanent — one listener each for
	// the app's lifetime. That is a decision, so it has to be stated.
	assert.match(
		composable,
		/Deliberately not removed/,
		"say which listeners outlive the caller, and why"
	)
})

test("the employee is told, on every screen", () => {
	// In App.vue, not per-page: a banner one screen owns is a banner the other
	// forty do not have.
	const app = read("App.vue")
	assert.match(app, /OfflineBanner|useOnline/, "the shell carries it")
})

test("an offline notice is a status, not an alert", () => {
	// §14: a change the employee did not cause must reach a screen reader, and
	// politely — `role="alert"` interrupts whatever is being read.
	const banner = read("components/OfflineBanner.vue")
	assert.match(banner, /role="status"/)
	assert.doesNotMatch(banner, /role="alert"/)
	assert.doesNotMatch(banner, /aria-live="assertive"/)
})

test("a new version waits to be let in", () => {
	const config = readFileSync(join(SRC, "../vite.config.js"), "utf8")
	assert.doesNotMatch(
		config,
		/registerType:\s*["']autoUpdate["']/,
		"autoUpdate reloads the page under a half-written form"
	)
	assert.match(config, /registerType:\s*["']prompt["']/, "ask first")
})

test("the service worker does not seize the page", () => {
	// Comments stripped first. The rule forbids a CALL at module scope, and the
	// comment explaining why names the call — the same defect three other gates
	// in this repo have already had (usage.mjs, the dvh rule, the sanitiser).
	const sw = readFileSync(join(SRC, "../public/sw.js"), "utf8")
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))
	// `skipWaiting()` at module scope activates the new worker the instant it
	// installs. It may only run when the PAGE asks — after the employee has
	// said yes — so the only permitted call is indented inside the listener.
	assert.doesNotMatch(
		sw,
		/^self\.skipWaiting\(\)/m,
		"unconditional skipWaiting takes over mid-session"
	)
	assert.match(sw, /"SKIP_WAITING"/, "it waits for the page to tell it")
	assert.match(sw, /addEventListener\(\s*"message"/, "through one message, not a timer")
})

test("the prompt to reload is offered, not forced", () => {
	const app = read("App.vue")
	assert.match(app, /UpdatePrompt|needRefresh/, "the shell offers the reload")
})

// The offline bar must not COVER the screen it is warning about. `.g-header`
// is transparent and sits in NORMAL FLOW at the top of every page — the
// comment on it says so in as many words, and the back control is its first
// child. A `position: fixed; top: 0` bar therefore lands directly on that
// back button: the employee is told they have no connection and loses the
// control that would take them somewhere useful. The checklist's own rule:
// "sticky headers/navigation do not cover content".
test("the offline bar pushes the page down, it does not sit on it", () => {
	const css = readFileSync(join(SRC, "theme/glass-components.css"), "utf8")
	const bar = css.slice(
		css.indexOf("\n.g-offline {"),
		css.indexOf("}", css.indexOf("\n.g-offline {"))
	)
	assert.doesNotMatch(bar, /position:\s*fixed/, "fixed puts it over .g-header's back button")
	// The app shell reserves the room instead, so every screen moves down by
	// exactly the bar's height while it is showing and by nothing when it is not.
	// In flow, as the FIRST child of <ion-app>: the bar occupies real height,
	// so the router outlet below it moves down by exactly that and back up
	// when it goes. No second source of truth for the bar's height, which a
	// reserved-padding approach would need and would drift from.
	assert.match(bar, /position:\s*relative/, "in flow, so it takes its own room")
	const app = read("App.vue")
	const outlet = app.indexOf("<ion-router-outlet")
	const banner = app.indexOf("<OfflineBanner")
	assert.ok(banner > 0 && banner < outlet, "and it is ABOVE the outlet, or it pushes nothing")
})

// The update prompt is at the BOTTOM, where the tab bar lives and where most
// screens put their primary action. It must clear both.
test("the update prompt clears the tab bar and its safe area", () => {
	const css = readFileSync(join(SRC, "theme/glass-components.css"), "utf8")
	const prompt = css.slice(
		css.indexOf("\n.g-update {"),
		css.indexOf("}", css.indexOf("\n.g-update {"))
	)
	assert.match(prompt, /--g-tabbar-height/, "offset by the tab bar's own token, not a guess")
	assert.match(prompt, /env\(safe-area-inset-bottom/, "and the home indicator below it")
})
