// An empty state must never render beside the error state (runtime crawl,
// 15 Sep 2026).
//
// /sop/<missing> showed BOTH "Could not load" and "Nothing to show yet":
// SopDetail drew `<ResourceError :resource="sop">` and, below it,
// `<GEmptyState v-else-if="!sop.loading">`. `!X.loading` means "finished",
// and a failed request is finished too — so the empty state told the reader
// there was nothing here while the line above said we could not find out.
//
// The order is loading → error → empty → content. This walks every template
// and flags an empty-state branch whose if-chain waits for `!X.loading` but
// never mentions `X.error`, in a file that draws a ResourceError for that same
// X. Narrow on purpose: an empty state gated on data alone, or a chain that
// already names the error, is not flagged — zero false positives over recall.
import { test } from "node:test"
import assert from "node:assert/strict"
import { parse as parseSfc } from "@vue/compiler-sfc"
import { sourceFiles, sfc, rel } from "./_lib.mjs"

const ELEMENT = 1
const TEXT = 2
const COMMENT = 3
const DIRECTIVE = 7
const EMPTY_STATES = new Set(["GEmptyState"])

const directive = (node, name) =>
	node.props?.find((p) => p.type === DIRECTIVE && p.name === name)
const condition = (node) =>
	(directive(node, "if") || directive(node, "else-if"))?.exp?.content || null
const escape = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")

// Resources a template shows an error state for: `<ResourceError :resource="X">`.
function errorStateResources(node, out = new Set()) {
	if (node.type === ELEMENT && node.tag === "ResourceError") {
		const bound = node.props.find(
			(p) =>
				p.type === DIRECTIVE &&
				p.name === "bind" &&
				p.arg?.content === "resource"
		)
		if (bound?.exp?.content) out.add(bound.exp.content.trim())
	}
	for (const child of node.children || []) errorStateResources(child, out)
	return out
}

// The conditions of a node's v-if / v-else-if chain, up to and including it.
function chainConditions(siblings, index) {
	const conditions = [condition(siblings[index])]
	if (!directive(siblings[index], "else-if")) return conditions
	for (let i = index - 1; i >= 0; i--) {
		const node = siblings[i]
		if (node.type === COMMENT || (node.type === TEXT && !node.content.trim()))
			continue
		if (node.type !== ELEMENT) break
		const own = condition(node)
		if (own) conditions.unshift(own)
		if (!directive(node, "else-if")) break // reached the v-if head
	}
	return conditions
}

// [line, resource] for every empty state that can render beside its error.
export function flagsIn(ast) {
	const withErrorState = errorStateResources(ast)
	const out = []
	const walk = (node) => {
		const children = node.children || []
		children.forEach((child, index) => {
			if (
				child.type === ELEMENT &&
				EMPTY_STATES.has(child.tag) &&
				condition(child)
			) {
				const chain = chainConditions(children, index).join(" ")
				for (const resource of withErrorState) {
					const waitsForLoad = new RegExp(
						`!\\s*${escape(resource)}\\.loading\\b`
					).test(chain)
					const namesError = new RegExp(
						`\\b${escape(resource)}\\.error\\b`
					).test(chain)
					if (waitsForLoad && !namesError)
						out.push([child.loc.start.line, resource])
				}
			}
			walk(child)
		})
	}
	walk(ast)
	return out
}

test("no empty state renders beside its resource's error state", () => {
	const found = []
	for (const file of sourceFiles()) {
		if (!file.endsWith(".vue")) continue
		const ast = sfc(file).descriptor.template?.ast
		if (!ast) continue
		for (const [line, resource] of flagsIn(ast))
			found.push(
				`${rel(file)}:${line} empty state shows beside ${resource}'s error`
			)
	}
	assert.deepEqual(found, [])
})

test("the audit flags the SopDetail shape and passes its fix (self-check)", () => {
	// If the compiler's AST shape drifts, the scan above would pass vacuously.
	const bad = `<template><div>
		<ResourceError :resource="sop" what="x" />
		<div v-if="sop.data">content</div>
		<!-- a comment between branches is still one chain -->
		<GEmptyState v-else-if="!sop.loading" title="none" />
	</div></template>`
	const astOf = (source) =>
		parseSfc(source, { filename: "SelfCheck.vue" }).descriptor.template.ast
	assert.equal(flagsIn(astOf(bad)).length, 1)
	assert.equal(
		flagsIn(
			astOf(bad.replace('"!sop.loading"', '"!sop.loading && !sop.error"'))
		).length,
		0
	)
	// the error named in an EARLIER branch of the chain also excludes it
	const earlier = bad.replace('v-if="sop.data"', 'v-if="sop.error || sop.data"')
	assert.equal(flagsIn(astOf(earlier)).length, 0)
})
