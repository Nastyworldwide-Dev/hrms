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

const siteSkip = (gate) => ({ gate, code: 0, info: { status: "skip" } });
const SITE = ["a11y", "visual", "coherence", "ios"];

test("a named skip is allowed under --strict, an unnamed one is not", () => {
	// CI has no served site: it names the four site gates, and only those
	const board = [ok, siteSkip("a11y"), siteSkip("visual"), siteSkip("coherence"), siteSkip("ios")];
	assert.equal(gatesFailed(board, true, SITE), false);
	assert.equal(gatesFailed(board, true), true);
	assert.equal(gatesFailed(board, true, ["a11y"]), true);
});

test("allowing the site gates to skip never excuses another gate's skip", () => {
	const board = [siteSkip("tokens"), siteSkip("a11y")];
	assert.equal(gatesFailed(board, true, SITE), true);
});

test("allowed skips do not excuse a failure, even in a site gate", () => {
	const crashed = { gate: "visual", code: 1, info: {} };
	assert.equal(gatesFailed([ok, crashed], true, SITE), true);
	assert.equal(gatesFailed([ok, crashed], false, SITE), true);
});
