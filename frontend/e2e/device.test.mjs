import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { asInstalled, STATUS_BAR_STYLE } from "./device.mjs"

test("safe-area insets become the iPhone's, with or without a fallback", () => {
	assert.equal(asInstalled("top: env(safe-area-inset-top, 0px);"), "top: 0px;")
	assert.equal(asInstalled("padding: env(safe-area-inset-bottom)"), "padding: 34px")
	assert.equal(asInstalled("calc(env(safe-area-inset-bottom, 0px) + 8px)"), "calc(34px + 8px)")
	assert.equal(asInstalled("--ion-safe-area-top: constant(safe-area-inset-top);"), "--ion-safe-area-top: 0px;")
	assert.equal(asInstalled("max(16px, env(safe-area-inset-left, var(--x)))"), "max(16px, 0px)")
})

test("the standalone media query matches, as it does from the Home Screen", () => {
	assert.equal(asInstalled("@media (display-mode: standalone) {"), "@media (min-width: 0px) {")
})

test("the insets assume the status-bar style index.html really sets", () => {
	const html = readFileSync(new URL("../index.html", import.meta.url), "utf8")
	const style = html.match(/apple-mobile-web-app-status-bar-style" content="([^"]+)"/)[1]
	assert.equal(style, STATUS_BAR_STYLE)
})
