// Guards the Team Roster resources' endpoints. A silent typo here (wrong
// method path) would break the roster with no build error — the resource just
// 404s at runtime. Reads the source like the other data guards so it needs no
// frappe-ui context.

import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { test } from "node:test"

const src = readFileSync(fileURLToPath(new URL("./team.js", import.meta.url)), "utf8")

test("teamRoster reads the fenced get_team_roster endpoint", () => {
	assert.match(src, /teamRoster[\s\S]*?url:\s*"hrms\.api\.team\.get_team_roster"/)
})

test("assignShift writes through the fenced insert_shift endpoint", () => {
	// insert_shift is wrapped by _ensure_can_roster on the server — the UI is
	// never the security boundary. If this ever points at an unfenced method,
	// the roster loses its team/company fence.
	assert.match(src, /assignShift[\s\S]*?url:\s*"hrms\.api\.roster\.insert_shift"/)
})
