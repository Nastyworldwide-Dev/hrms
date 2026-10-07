// The surfaces gate must follow its own rule 3: "a closed sheet's contents
// never count toward the screen". More.vue read 7/6 because a one-line
// `<Child v-if=... />` inside a GModal left its cost in the pending v-if
// branch; `</GModal>` then closed the sheet, and the branch was flushed later
// onto the SCREEN. The real screen has 5. This runs the gate over a tiny
// source tree (SURFACES_SRC) with that exact shape.

import assert from "node:assert/strict";
import test from "node:test";
import { spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const GATE = join(dirname(fileURLToPath(import.meta.url)), "surfaces.mjs");

function run(files) {
	const src = mkdtempSync(join(tmpdir(), "surfaces-"));
	try {
		for (const [rel, body] of Object.entries(files)) {
			mkdirSync(dirname(join(src, rel)), { recursive: true });
			writeFileSync(join(src, rel), body);
		}
		const res = spawnSync(process.execPath, [GATE, "--report-only"], {
			encoding: "utf8",
			env: { ...process.env, SURFACES_SRC: src },
		});
		assert.equal(res.status, 0, res.stderr);
		return res.stdout;
	} finally {
		rmSync(src, { recursive: true, force: true });
	}
}

const panel = `<template><div class="g-glass"></div></template>\n`;
const card = `<template><div class="g-glass"></div><div class="g-glass"></div></template>\n`;
const modal = `<template><div><slot /></div></template>\n`;

test("a v-if child inside a sheet counts toward the sheet, not the screen", () => {
	const out = run({
		"components/Panel.vue": panel,
		"components/Card.vue": card,
		"components/GModal.vue": modal,
		"views/Sheety.vue": `<template>
	<div>
		<Panel />
		<GModal
			:is-open="open"
			title="Sheet"
		>
			<Card v-if="open && ready" />
		</GModal>
		<template v-if="more">
			<Panel />
		</template>
	</div>
</template>
`,
	});
	const row = out.split("\n").find((l) => l.includes("views/Sheety.vue"));
	assert.ok(row, out);
	// two panels on the screen (1 + 1); the card (2) belongs to the sheet
	assert.match(row, /\s2\/6\s+\(content 2\)/, row);
	assert.match(row, /sheets: 2$/, row);
});

test("a v-if child outside any sheet still counts on the screen", () => {
	const out = run({
		"components/Panel.vue": panel,
		"components/Card.vue": card,
		"components/GModal.vue": modal,
		"views/Plain.vue": `<template>
	<div>
		<Card v-if="ready" />
		<Panel />
	</div>
</template>
`,
	});
	const row = out.split("\n").find((l) => l.includes("views/Plain.vue"));
	assert.ok(row, out);
	assert.match(row, /\s3\/6\s+\(content 3\)/, row);
});
