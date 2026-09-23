// Error toasts carry the server's reason (static audit, 15 Sep 2026).
//
// A boss reported that an employee "could not apply for leave — unknown
// error". FormView's insert handler toasted the generic "Error creating Leave
// Application" and dropped the server's own message (insufficient balance,
// outside the allocation period, approver not designated), so every refusal
// looked like the same unknown fault (bc87ecf50). The reader for that message
// is ONE function — utils/loudRequest.firstMessage — which also strips the
// Desk links and <strong> markup a refusal carries, because frappe-ui's Toast
// renders `text` with v-html (8c30eedf5).
//
// This walks every onError / catch handler in src/ and requires each toast
// inside it to build its text through firstMessage(). A raw
// `error.messages?.[0]` is refused too: it is the unstripped, link-carrying
// form that 8c30eedf5 removed.
import { test } from "node:test"
import assert from "node:assert/strict"
import { sourceFiles, read, rel, lineOf } from "./_lib.mjs"

// Handlers whose failure is not a server refusal, with the reason on record.
const EXEMPT = {
	// Browser Notification / push-subscription errors; deliberately calm copy.
	"src/components/PushNotificationPrompt.vue":
		"push enable is optional; calm copy by design",
	"src/views/Profile.vue":
		"browser Notification API errors, not server refusals",
}

// `onError(...) {` / `onError: (e) => {` / `.catch((e) => {` / `catch (e) {`
const HANDLER_RE =
	/\bonError\b\s*(?::\s*)?(?:async\s*)?(?:\([^)]*\)|\w+)?\s*(?:=>)?\s*\{|\.catch\(\s*(?:async\s*)?(?:\([^)]*\)|\w+)\s*=>\s*\{|\bcatch\s*(?:\([^)]*\))?\s*\{/g

function blockAt(text, openBrace) {
	let depth = 0
	for (let i = openBrace; i < text.length; i++) {
		const c = text[i]
		if (c === "{") depth++
		else if (c === "}" && --depth === 0) return text.slice(openBrace, i + 1)
		else if (c === "`" || c === '"' || c === "'") {
			const close = text.indexOf(c, i + 1)
			if (close !== -1) i = close
		}
	}
	return text.slice(openBrace)
}

function callAt(text, openParen) {
	let depth = 0
	for (let i = openParen; i < text.length; i++) {
		const c = text[i]
		if (c === "(") depth++
		else if (c === ")" && --depth === 0) return text.slice(openParen, i + 1)
	}
	return text.slice(openParen)
}

export function auditToasts(text, file) {
	const findings = []
	for (const m of text.matchAll(HANDLER_RE)) {
		const open = text.indexOf("{", m.index + m[0].length - 1)
		const body = blockAt(text, open)
		for (const t of body.matchAll(/\btoast\(/g)) {
			const call = callAt(body, t.index + "toast".length)
			const at = lineOf(text, open + t.index)
			if (/\bmessages(?:\?\.|\.)?\s*\[\s*0\s*\]|\bmessages\??\.join/.test(call))
				findings.push(
					`${file}:${at} reads error.messages directly — use firstMessage() (strips Desk markup)`
				)
			else if (!/\bfirstMessage\(/.test(call))
				findings.push(
					`${file}:${at} error toast without the server message — use firstMessage()`
				)
		}
	}
	return findings
}

test("every error toast surfaces the server's message through firstMessage()", () => {
	const findings = []
	for (const file of sourceFiles()) {
		if (rel(file) in EXEMPT) continue
		if (rel(file) === "src/utils/loudRequest.js") continue // the helper itself
		findings.push(...auditToasts(read(file), rel(file)))
	}
	assert.deepEqual(findings, [], findings.join("\n"))
})

test("the audit catches the shape bc87ecf50 fixed", () => {
	const bad = `
const x = createResource({
	url: "a",
	onError() {
		toast({ title: "Error", text: __("Error creating {0}", [doctype]) })
	},
})`
	assert.equal(auditToasts(bad, "x.vue").length, 1)
	const raw = `p.catch((error) => { toast({ text: error?.messages?.[0] || "x" }) })`
	assert.equal(auditToasts(raw, "y.js").length, 1)
	const good = `try { a() } catch (error) { toast({ text: firstMessage(error, "x") }) }`
	assert.deepEqual(auditToasts(good, "z.js"), [])
})

test("every exemption still names a file that exists", () => {
	const files = new Set(sourceFiles().map(rel))
	for (const file of Object.keys(EXEMPT))
		assert.ok(files.has(file), `${file} no longer exists — drop the exemption`)
})
