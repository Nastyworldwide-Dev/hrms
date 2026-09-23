// The screens that are TAB ROOTS, and therefore must NOT carry a back control
// (§12, v1.11). Everything else is pushed and must. Kept beside the gate rather
// than derived from navItems.js so the rule is stated once, in the place that
// enforces it, and a route moving between tab and pushed is a visible edit here.
//
// login and invalid-employee are neither: login has no parent, and
// invalid-employee is a terminal error state with its own way out.
// The 2.0 tab bar (slice 0.1, 22 Sep 2026): Home · Calendar · Requests ·
// Score · More. Calendar and Score are RENAMES over the same routes, so their
// screen ids are unchanged; `requests` is the new hub, and `dash-leaves` and
// `dash-expense-claims` lost their tab — they are reached through More now,
// which makes them ordinary screens rather than roots.
//
// This gate skips without a running site, so it did not complain when the bar
// changed underneath it. A stale root list is the kind of thing that only
// speaks up months later, on the one run somebody has a site.
export const TAB_ROOTS = new Set([
	"home",
	"dash-attendance", // Calendar
	"requests",
	"dash-kpi", // Score
	"more",
	"login",
	// /forgot-password has no route of its own: it renders Login, the entry
	// screen, which has nothing to go back to (alpha.5 served run).
	"forgot-password",
	"invalid-employee",
]);
