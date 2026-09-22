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
	// The per-component `onConnectivityChange` helper that used to live here
	// was exported and never imported — the dead-code audit found it on
	// 22 Sep 2026 — so it is gone rather than kept for a caller that never
	// arrived. What it used to need pinning for (both listeners coming off in
	// onScopeDispose) no longer exists to break.
	//
	// The SHARED pair is deliberately permanent — one listener each for the
	// app's lifetime. That is a decision, so it has to be stated, and this is
	// the assertion that keeps it stated.
	assert.match(
		composable,
		/Deliberately not removed/,
		"say which listeners outlive the caller, and why"
	)
	// And there is exactly ONE wiring site. Two would be two answers.
	assert.equal(
		(composable.match(/addEventListener\(\s*["']online["']/g) || []).length,
		1,
		"one place wires connectivity; a second would be a second answer"
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
test("the offline bar never covers the header", () => {
	const css = readFileSync(join(SRC, "theme/glass-components.css"), "utf8")
	const bar = css.slice(
		css.indexOf("\n.g-offline {"),
		css.indexOf("}", css.indexOf("\n.g-offline {"))
	)
	// `ion-router-outlet` is `position: absolute` pinned to all four edges —
	// read from @ionic/core's own router-outlet.css — so NOTHING in normal
	// flow can push it down. Being first in <ion-app> moves nothing; the bar
	// simply painted over the header again, which is the defect the previous
	// fix was for.
	//
	// So the outlet is inset instead: one custom property, set while the bar
	// is showing, that the outlet's `top` reads. One source of truth for the
	// height, and the bar is the thing that owns it.
	assert.match(bar, /position:\s*fixed/, "over the page, because the outlet cannot be pushed")
	// Comments stripped: the block ABOVE the rule explains why the outlet is
	// inset and names `ion-router-outlet`, so an unstripped read matches the
	// explanation instead of the declaration. Sixth time today.
	const shell = readFileSync(join(SRC, "theme/glass-components.css"), "utf8").replace(
		/\/\*[\s\S]*?\*\//g,
		(b) => b.replace(/[^\n]/g, " ")
	)
	assert.match(
		shell,
		/ion-router-outlet\s*\{[\s\S]*?top:\s*var\(--g-offline-height/,
		"the outlet starts BELOW the bar, so the header is never covered"
	)
	assert.match(
		shell,
		/--g-offline-height:\s*0/,
		"and the inset is zero when the bar is not showing"
	)
	// The inset is a class on <html>, so SOMETHING has to set it — a rule
	// nobody toggles insets nothing, and the bar covers the header again with
	// every declaration in place. The banner owns it, because the banner is
	// what knows whether it is showing.
	const banner = read("components/OfflineBanner.vue")
	assert.match(
		banner,
		/classList\.toggle\(\s*"is-offline"/,
		"the bar toggles the class the outlet's inset hangs on"
	)
	assert.match(
		shell,
		/\.is-offline\s*\{[\s\S]*?--g-offline-height:/,
		"and the class sets the height"
	)
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
