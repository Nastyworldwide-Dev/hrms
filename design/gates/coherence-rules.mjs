// The screens that are TAB ROOTS, and therefore must NOT carry a back control
// (§12, v1.11). Everything else is pushed and must. Kept beside the gate rather
// than derived from navItems.js so the rule is stated once, in the place that
// enforces it, and a route moving between tab and pushed is a visible edit here.
//
// login and invalid-employee are neither: login has no parent, and
// invalid-employee is a terminal error state with its own way out.
export const TAB_ROOTS = new Set([
	"home",
	"dash-attendance",
	"dash-leaves",
	"dash-expense-claims",
	"more",
	"login",
	"invalid-employee",
]);
