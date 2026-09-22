// Forms that explain themselves, and failures somebody can investigate
// (pre-2.0 R4, checklist §4 §5 §16).
//
// The audit that produced this file expected to find far more than it did.
// GInput and GTextarea already wrap their control in a <label>, already set
// `aria-invalid` when they carry an error, already render that error in a live
// region; GModal already carries the focus trap the raw ion-modal did not.
// Most of §4 and §5 is built. Two things are not.
//
// THE ERROR IS NOT LINKED TO THE FIELD. `aria-invalid` says "this is wrong";
// only `aria-describedby` says WHAT is wrong. Without it a screen reader
// announces "Reason, invalid, edit text" and the sentence explaining why sits
// in a live region that has already been read and moved on. The checklist asks
// that errors be connected to their fields, and that is the connection.
//
// NOTHING RECORDS A FAILURE. When an employee says "I submitted it yesterday
// and my manager cannot see it", there is nothing to look at: no captured
// error, no build id, no way to tell which version of the app they were
// running. §16 exists for exactly that sentence.
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

const FIELDS = ["components/glass/GInput.vue", "components/glass/GTextarea.vue"]

test("a field's error is announced with the field, not after it", () => {
	for (const field of FIELDS) {
		const source = read(field)
		assert.match(source, /aria-invalid/, `${field} should already flag the state`)
		assert.match(
			source,
			/aria-describedby/,
			`${field}: aria-invalid says THAT it is wrong; describedby says what`
		)
		// The id has to be unique per instance — two invalid fields on one form
		// pointing at the same id means the second describes the first's error.
		// The BINDING, not a mention: `const errorId = "field-error"` still
		// contains the word errorId and gives every instance on the page the
		// same id, so the second invalid field describes the first one's error.
		assert.match(
			source,
			/const errorId = useId\(\)/,
			`${field}: the id must come from useId, one per instance`
		)
	}
})

test("the error element carries the id the field points at", () => {
	for (const field of FIELDS) {
		const source = read(field)
		const error = source.match(/<span[^>]*g-field__error[^>]*>/)
		assert.ok(error, `${field} renders its error`)
		assert.match(error[0], /:id=/, `${field}: describedby points at nothing without an id here`)
	}
})

// A failure the employee saw and nobody can see afterwards is the whole reason
// §16 exists. Not a service: one place that records what broke, with enough to
// find it again.
test("something records a failure", () => {
	const reporter = read("utils/diagnostics.js")
	assert.match(reporter, /addEventListener\(\s*["']error["']/, "an uncaught error")
	assert.match(
		reporter,
		/addEventListener\(\s*["']unhandledrejection["']/,
		"and a rejected promise"
	)
	assert.match(
		reporter,
		/app\.config\.errorHandler|errorHandler/,
		"and a component that threw while rendering"
	)
})

test("a report says which build it came from", () => {
	const config = readFileSync(join(SRC, "../vite.config.js"), "utf8")
	assert.match(config, /__APP_BUILD__/, "the build stamps itself at compile time")
	assert.match(read("utils/diagnostics.js"), /__APP_BUILD__/, "and every report carries it")
})

test("a report never carries what it must not", async () => {
	// Exercised, not grepped: a `redact` that is imported and never called
	// still puts the word in the file. Capture what report() actually writes.
	const { report } = await import("../utils/diagnostics.js")
	const written = []
	const original = console.error
	console.error = (...args) => written.push(args)
	try {
		report("test", new Error("x"), {
			password: "hunter2",
			api_key: "sk-live-1",
			basic_salary: 9000,
			nested: { session_token: "abc", employee_name: "Ada" },
		})
	} finally {
		console.error = original
	}
	const dump = JSON.stringify(written)
	for (const secret of ["hunter2", "sk-live-1", "9000", "abc"]) {
		assert.ok(!dump.includes(secret), `${secret} reached the log`)
	}
	// ...and redaction is not a synonym for silence: the SHAPE survives, so a
	// reader can still see which field was involved.
	assert.ok(dump.includes("[redacted]"), "the keys are still named")
	assert.ok(dump.includes("Ada"), "a non-sensitive value is kept")
})

test("reporting a failure cannot itself fail the app", async () => {
	// A reporter that throws inside an error handler takes the page with it and
	// loses the error it was reporting. Make the sink itself throw.
	const { report } = await import("../utils/diagnostics.js")
	const original = console.error
	console.error = () => {
		throw new Error("the console is gone")
	}
	try {
		assert.doesNotThrow(
			() => report("test", new Error("x")),
			"report() must swallow its own failure"
		)
	} finally {
		console.error = original
	}
})

test("the diagnostics seam is used, not merely written", () => {
	const main = read("main.js")
	assert.match(main, /diagnostics/, "main.js installs it")
	const files = walk(SRC).map((p) => readFileSync(p, "utf8"))
	assert.ok(
		files.some((t) => /installDiagnostics\(/.test(t)),
		"and something calls it"
	)
})

// The header claimed redaction was "enforced HERE" and it was enforced on
// `detail` only — the error itself went to the log untouched. A Frappe failure
// arrives as an Error whose message embeds the server's sentence and whose
// `response`/`_server_messages` ride along as properties, which is the most
// ordinary shape in this app. Security review of b7a23bc7c, CRITICAL.
test("the error object is redacted too, not just the detail", async () => {
	const { report } = await import("../utils/diagnostics.js")
	const written = []
	const original = console.error
	console.error = (...args) => written.push(args)
	try {
		const error = new Error("Basic Salary must be positive, got 4500 (bank_account: 1234567890)")
		error.response = { data: { session_token: "sk-live-1", _server_messages: "9000" } }
		report("leave.submit", error)
	} finally {
		console.error = original
	}
	const dump = JSON.stringify(written)
	for (const secret of ["sk-live-1", "1234567890"]) {
		assert.ok(!dump.includes(secret), `${secret} reached the log through the error object`)
	}
	// The error must still be USEFUL: its type and where it happened survive,
	// because a redacted report nobody can act on is the same as no report.
	assert.ok(dump.includes("Error"), "the error's type is kept")
	assert.ok(dump.includes("leave.submit"), "and where it happened")
})

// Depth was fail-OPEN: past four levels the value was returned raw. A Frappe
// error body nests further than that in normal use, so the one case the limit
// exists for was the case it stopped protecting.
test("too deep is dropped, not waved through", async () => {
	const { report } = await import("../utils/diagnostics.js")
	const written = []
	const original = console.error
	console.error = (...args) => written.push(args)
	try {
		report("x", new Error("x"), { a: { b: { c: { d: { e: { token: "sk-deep-1" } } } } } })
	} finally {
		console.error = original
	}
	assert.ok(
		!JSON.stringify(written).includes("sk-deep-1"),
		"a value past the depth limit was logged raw"
	)
})
