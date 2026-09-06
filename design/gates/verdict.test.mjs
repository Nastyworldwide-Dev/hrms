import assert from "node:assert/strict";
import test from "node:test";

import { gatesFailed } from "./verdict.mjs";

const ok = { code: 0, info: { status: "ok" } };
const skip = { code: 0, info: { status: "skip" } };
const failed = { code: 1, info: {} };

test("all gates pass -> board passes in both modes", () => {
	assert.equal(gatesFailed([ok, ok], false), false);
	assert.equal(gatesFailed([ok, ok], true), false);
});

test("a nonzero gate fails the board in both modes", () => {
	assert.equal(gatesFailed([ok, failed], false), true);
	assert.equal(gatesFailed([ok, failed], true), true);
});

test("a skipped gate passes lenient but FAILS --strict", () => {
	// the regression: run.mjs used to exit 0 here even under --strict
	assert.equal(gatesFailed([ok, skip], false), false);
	assert.equal(gatesFailed([ok, skip], true), true);
});
