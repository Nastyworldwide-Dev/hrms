// No frappe-ui UI CONTROLS in the app's screens and components (owner ruling:
// no frappe-ui buttons, switches or spinners in the app; the Glass kit under
// components/glass has one of each).
//
// A frappe-ui Button beside a GButton is two buttons with two focus rings,
// two disabled looks and two loading treatments on one screen — and a
// LoadingIndicator is a spinner, which the design spec bans (§11.2: skeletons,
// no spinners anywhere). Data helpers (createResource, toast, call, …) and the
// rich TextEditor are NOT controls and stay allowed.
//
// ALLOW_LIST: files still importing a banned control, each with the reason.
// Shrink it; never grow it without a reason a reviewer can check.
//   node --test tests/audit/no-frappe-ui-controls.test.mjs
import test from "node:test"
import assert from "node:assert/strict"
import { join } from "node:path"

import { SRC, sourceFiles, read, rel } from "./_lib.mjs"

const BANNED = [
	"Button",
	"Switch",
	"Badge",
	"LoadingIndicator",
	"Autocomplete",
	"Dialog",
	"Dropdown",
	"ErrorMessage",
]

//: file (relative to frontend/) -> banned names it may still import, and why.
export const ALLOW_LIST = {
	"src/components/FormView.vue": {
		names: ["ErrorMessage"],
		why: "the form's server error line; the ⋯ menu and the confirm dialogs went Glass in alpha.7 Phase 4",
	},
}

function bannedImports(text) {
	const found = []
	for (const match of text.matchAll(/import\s*\{([^}]*)\}\s*from\s*["']frappe-ui["']/g)) {
		for (const raw of match[1].split(",")) {
			const name = raw.trim().split(/\s+as\s+/)[0]
			if (BANNED.includes(name)) found.push(name)
		}
	}
	return found
}

test("the scanner sees a banned control and ignores a data helper", () => {
	assert.deepEqual(
		bannedImports('import { createResource, Button, toast } from "frappe-ui"'),
		["Button"]
	)
	assert.deepEqual(bannedImports('import { TextEditor, call } from "frappe-ui"'), [])
})

test("no view or component imports a frappe-ui UI control", () => {
	const offenders = []
	for (const dir of ["views", "components"]) {
		for (const file of sourceFiles(join(SRC, dir))) {
			const allowed = ALLOW_LIST[rel(file)]?.names || []
			const bad = bannedImports(read(file)).filter((name) => !allowed.includes(name))
			if (bad.length) offenders.push(`${rel(file)}: ${bad.join(", ")}`)
		}
	}
	assert.deepEqual(offenders, [], "use the Glass control instead (components/glass/*)")
})

test("every allow-list entry still needs to be there, with a reason", () => {
	for (const [file, entry] of Object.entries(ALLOW_LIST)) {
		assert.ok(entry.why?.length > 10, `${file} needs a reason`)
		const still = bannedImports(read(join(SRC, "..", file)))
		for (const name of entry.names)
			assert.ok(still.includes(name), `${file} no longer imports ${name}: drop it`)
	}
})
