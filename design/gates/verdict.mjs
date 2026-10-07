// The board's exit verdict, isolated so it is testable without spawning gates.
//
// A gate that exits nonzero always fails the board. Under --strict a gate that
// MEASURED NOTHING (clean exit but status:"skip" — no served site / no AUDIT_PW)
// is ALSO fatal: the documented promise of --strict is that a skip cannot pass,
// and run.mjs's exit used to ignore skips entirely, so `yarn gates --strict`
// returned 0 while three browser gates measured nothing. A crashed gate has
// code!==0 so it is already caught here — a missing GATE_RESULT never masks it.
//
// allowedSkips names gates whose skip is expected on THIS runner (CI has no
// served site, so GATES_NO_SITE=1 names the four site gates). Only a skip by a
// named gate is excused: a skip anywhere else, or any nonzero exit, still fails.
export function gatesFailed(results, strict, allowedSkips = []) {
	if (results.some((r) => r.code !== 0)) return true;
	return Boolean(
		strict && results.some((r) => r.info?.status === "skip" && !allowedSkips.includes(r.gate)),
	);
}
