// The lg: contrast proof must be computed from the SAME content-column width
// the app ships, not from a literal copied into the gate.
//
// contrast.mjs:188 read `column: 720` while --g-content-column-lg lived in
// tokens.json. tokens.json describes that value as "a starting value, expected
// to be tuned once on device — which is why the spec insists it be a single
// token", so the one edit it exists to receive is exactly the edit its proof
// could not see. Widening it to 880 makes the column reach blob B at 1024px
// dark (ink-muted 4.31:1, under the 4.5 floor); with the literal in place the
// gate stays green and reports the old geometry.
//
// This is a grep-shaped test on purpose. Asserting the number would pass the
// moment someone edits the literal to match, which is the defect.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(HERE, "contrast.mjs"), "utf8");
const tokens = JSON.parse(readFileSync(join(HERE, "..", "tokens.json"), "utf8"));

test("the lg: content column is read from tokens.json, not hardcoded", () => {
	const hardcoded = /column:\s*\d+/.exec(src);
	assert.equal(
		hardcoded,
		null,
		`contrast.mjs hardcodes ${hardcoded?.[0]}; it must read ` +
			"tokens.layout['content-column-lg'] so tuning the token re-proves the geometry",
	);
	assert.match(src, /content-column-lg/);
});

test("the token the gate depends on still exists and is a px length", () => {
	const v = tokens.layout?.["content-column-lg"]?.value;
	assert.ok(v, "tokens.layout['content-column-lg'] is missing");
	assert.match(v, /^\d+px$/, `expected a px length, got ${v}`);
});
