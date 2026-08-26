// GTag must render a NATIVE element, even when a component of the same
// capitalised name is globally registered.
//
// This pins the defect GTag exists to prevent. `main.js` does
// app.component("Button", Button), and Vue's resolveDynamicComponent tries the
// name, its camelCase form AND its capitalised form before falling back to a
// tag — so `<component :is="'button'">` resolved to frappe-ui's Button in every
// Glass row, card and panel. frappe-ui's classes then overrode the Glass
// layout and its single slot wrapper stopped the icon well, body and chevron
// being flex children of the row. That is the whole "icons misaligned
// everywhere" symptom from the 8.x frontend audit.
//
// The second test is the important one: it proves the trap is still live, so
// if someone "simplifies" GTag back to <component :is> the first test fails
// and this one explains why.
//
// Run with: node --test "frontend/**/*.test.js"
//
// The collision with the native <button> element is the exact defect this
// file exists to pin; a component literally named "Button" is the test
// fixture, not a mistake.
/* eslint-disable vue/no-reserved-component-names */
import { test } from "node:test"
import assert from "node:assert/strict"
import { createSSRApp, h, resolveDynamicComponent } from "vue"
import { renderToString } from "vue/server-renderer"

import GTag from "../GTag.js"

/** Stand-in for frappe-ui's globally registered Button. */
const RegisteredButton = {
	name: "Button",
	render() {
		return h("div", { class: "frappe-ui-button" }, "WRONG COMPONENT")
	},
}

test("renders a real <button> despite a registered Button component", async () => {
	const app = createSSRApp({
		render: () => h(GTag, { as: "button", type: "button", class: "g-row" }, () => "Request Leave"),
	})
	app.component("Button", RegisteredButton)

	const html = await renderToString(app)
	assert.match(html, /^<button/, "must render a native <button> element")
	assert.doesNotMatch(html, /frappe-ui-button/, "must not resolve to the registered Button")
	assert.match(html, /class="g-row"/, "class must fall through to the element")
	assert.match(html, /Request Leave/, "slot content must render")
})

test("the div branch renders a real <div>", async () => {
	const app = createSSRApp({
		render: () => h(GTag, { as: "div", class: "g-row" }, () => "read-only row"),
	})
	app.component("Button", RegisteredButton)

	const html = await renderToString(app)
	assert.match(html, /^<div/, "non-tappable rows must be a plain div")
})

test("THE TRAP: a dynamic :is string still resolves to the registered component", async () => {
	// Not a test of GTag — a test that the hazard GTag works around is real.
	// If Vue ever stops doing this, GTag can be deleted; until then it cannot.
	let resolved
	const app = createSSRApp({
		render() {
			resolved = resolveDynamicComponent("button")
			return h("div")
		},
	})
	app.component("Button", RegisteredButton)
	await renderToString(app)

	assert.notEqual(
		resolved,
		"button",
		"resolveDynamicComponent('button') returning the string would mean the hazard is gone"
	)
	assert.equal(
		resolved,
		RegisteredButton,
		"it resolves to the registered Button, not the HTML tag"
	)
})
