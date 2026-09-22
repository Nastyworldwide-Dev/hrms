// The empty path IS the Score screen (revamp §6, slice A5).
//
// The deployed 2.0 screenshot that cost the most was Score: a single dashed
// "No appraisals yet" card with roughly two thirds of a phone screen of black
// beneath it. That is not a styling problem. For most employees, most of the
// year, there is no appraisal — so the empty state is not an edge case the
// screen falls back to, it is the screen, and it was never built.
//
// The question a person actually has is "am I late for something?". "No
// appraisals yet" does not answer it, which is why they ask HR instead.
//
// THE FENCE (revamp KR3). Everything the empty path shows is about the
// READER'S OWN cycle. An Appraisal Cycle is org configuration, not a person's
// data, and membership is checked against this employee's own appraisee row.
// No other employee's name or score may ever enter an empty state, and this
// slice adds no endpoint — `whats_next` rides the payload
// get_my_kpi_dashboard already returns (KR1).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")
const api = readFileSync(join(SRC, "../../hrms/api/kpi.py"), "utf8")

function code(text) {
	return text
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))
}

function py(text) {
	return text.replace(/(^|\n)(\s*)#[^\n]*/g, (m, nl, indent) => nl + indent)
}

test("an employee with no appraisal is told when their review opens", () => {
	const view = code(read("views/kpi/Dashboard.vue"))
	// Not the presence of the word — the BRANCH. There are two empty paths now,
	// and the one that matters is the one that has something to say.
	assert.match(
		view,
		/v-else-if="dashboard\.data && !whatsNext"/,
		"nothing scheduled is its own state"
	)
	assert.match(view, /v-else-if="dashboard\.data"/, "and a scheduled cycle is another")
	assert.match(view, /nextCycleTitle/, "the scheduled state states what is coming")
	assert.match(view, /nextCycleBody/, "and when")
})

test("the date is in the sentence, not only in a table", () => {
	// A number on its own makes the reader do the joining. "It opens on 1 Oct"
	// is the whole answer; "Opens | 1 Oct" is a fact they have to assemble.
	const view = code(read("views/kpi/Dashboard.vue"))
	assert.match(view, /It opens on \{0\}|It closes on \{0\}/, "the date is stated in a sentence")
})

test("the cycle status is mapped, never translated raw", () => {
	// `__(status)` on a doctype Select renders the raw wire word, because the
	// translation files do not contain a doctype's own option values. The OT
	// compensation row and the attendance chip both carried this exact defect.
	const view = code(read("views/kpi/Dashboard.vue"))
	assert.doesNotMatch(view, /__\(\s*next\.status\s*[,)]/, "do not translate the wire value")
	assert.match(view, /"Not Started":\s*__\(/, "map it explicitly")
	assert.match(view, /"In Progress":\s*__\(/, "both of them")
})

test("the empty path adds no endpoint (KR1)", () => {
	// The revamp binds itself to reading what the existing fenced payload
	// already returns. A new whitelisted KPI endpoint is a new door.
	// Every door in this module, counted. The decorator carries a methods=
	// argument here, and the first version of this test matched the bare form
	// and found zero — a test that passes by finding nothing is not a test.
	const doors = [...api.matchAll(/@frappe\.whitelist\([^)]*\)\s*\ndef (\w+)/g)].map((m) => m[1])
	assert.deepEqual(
		doors.sort(),
		[
			"can_view_team_kpi",
			"get_department_kpi",
			"get_employee_kpi",
			"get_my_kpi_dashboard",
			"get_team_kpi",
		],
		"the KPI surface is exactly these five; the empty path opened none"
	)
	assert.match(api, /def _whats_next_for\(/, "it is a private helper")
	assert.match(api, /"whats_next": _whats_next_for\(employee\)/, "called on the empty branch only")
})

test("the empty path reads only this employee's own cycle (KR3)", () => {
	const source = py(api)
	const start = source.indexOf("def _whats_next_for(")
	const end = source.indexOf("\ndef ", start + 10)
	const body = source.slice(start, end)
	// Membership is checked against THIS employee. A query that read the
	// appraisee table without that filter would enumerate a cycle's roster.
	assert.match(
		body,
		/"Appraisee",\s*\{[^}]*"employee": employee/,
		"scoped to the caller's own row"
	)
	// And nothing here reads a person's results.
	for (const forbidden of ['Appraisal"', "pms_total_score", "overall_grade", "employee_name"]) {
		assert.ok(!body.includes(forbidden), `an empty state must not read ${forbidden}`)
	}
})

test("no appraisal scheduled is still an answer", () => {
	// Returning None and drawing nothing would put the screen back where it
	// started. The copy for that case says what will fill it, and says there
	// is nothing to do — which is the reassurance the whole slice exists for.
	const view = code(read("views/kpi/Dashboard.vue"))
	assert.match(view, /No review scheduled/, "it is named")
	assert.match(view, /nothing for you to do yet/i, "and the worry is answered")
})
