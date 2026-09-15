// A tab strip with one tab is a dead control (runtime crawl, 15 Sep 2026).
//
// /expense-claims/new drew a strip holding a single "Expenses" tab. Tapping it
// does nothing — it is already the active tab — so the crawl flagged it as a
// dead button, and it spends a sticky row of a phone screen saying nothing.
// The fields still render per tab; only the STRIP is gated on there being a
// choice to make.
import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { parse } from "@vue/compiler-sfc"

const ELEMENT = 1
const DIRECTIVE = 7
const source = readFileSync(new URL("../src/components/FormView.vue", import.meta.url), "utf8")
const ast = parse(source, { filename: "FormView.vue" }).descriptor.template.ast

// Every v-if condition on the path from the root to the first node matching `hit`.
function conditionsTo(node, hit, trail = []) {
	if (node.type !== ELEMENT && node.type !== 0) return null
	const own = node.props?.find((p) => p.type === DIRECTIVE && (p.name === "if" || p.name === "else-if"))
	const path = own ? [...trail, own.exp.content] : trail
	if (hit(node)) return path
	for (const child of node.children || []) {
		const found = conditionsTo(child, hit, path)
		if (found) return found
	}
	return null
}

const isTabButtonLoop = (node) =>
	node.props?.some((p) => p.type === DIRECTIVE && p.name === "for" && /\btab in tabs\b/.test(p.exp?.content || ""))

test("the tab strip renders only when there is more than one tab", () => {
	const conditions = conditionsTo(ast, isTabButtonLoop)
	assert.ok(conditions, "FormView still renders a tab strip")
	assert.ok(
		conditions.some((c) => /tabs\??\.length\s*>\s*1/.test(c)),
		`strip conditions ${JSON.stringify(conditions)} must require more than one tab`
	)
})

test("the per-tab field panes are not hidden with the strip", () => {
	const conditions = conditionsTo(ast, (node) =>
		node.props?.some((p) => p.type === DIRECTIVE && p.name === "for" && /in tabFields\b/.test(p.exp?.content || ""))
	)
	assert.ok(conditions, "fields still render per tab")
	assert.ok(
		!conditions.some((c) => /length\s*>\s*1/.test(c)),
		"a single-tab form must still show its fields"
	)
})
