// Sibling Frappe apps that live on the same site as the HRMS PWA and are
// reached by leaving it: Approva (/approva) and Project Board (/board).
// Helpdesk left this list in v16.23.0 — it has a native front end now
// (data/navItems.js HELPDESK_ITEM). Both apps each ship their own SPA under their own PWA scope, so vue-
// router cannot reach them — the row does a full navigation via `href`, not a
// `route`. Same origin means the Frappe session cookie carries over and the
// target opens signed in.
//
// Kept free of Vue imports so the data can be unit-tested under node; icons
// are attached in navItems.js (APP_ITEMS).
//
// `title` and `sublabel` are i18n source strings — wrap with $translate.
// `roles` is the allowlist that decides whether the row is OFFERED. It is not
// access control — each app enforces its own permissions on the far side, and
// a user who reaches /approva without rights meets Approva's wall, not ours.
// What the allowlist buys is that a row is not dangled in front of someone it
// cannot serve; before it, every employee saw both.
//
// The strings are ERPNext role names and they are easy to get wrong:
// "Projects User" / "Projects Manager" carry the plural. "Project Manager"
// (no s) is a Designation on Employee — a check against it matches no role at
// all, so the row would vanish for exactly the people meant to have it.
// app-links.test.js pins that.
//
// Approva's five match the allowlist ERPNext already uses for the
// finance-adjacent payroll report (intercompany_salary_cost_allocation.py) —
// the same operator set, so the two surfaces agree.
export const APP_LINKS = [
	{
		key: "approva",
		title: "Approva",
		sublabel: "Purchase requests & approvals",
		href: "/approva",
		roles: ["Accounts Manager", "Accounts User", "System Manager", "HR Manager", "HR User"],
	},
	{
		key: "board",
		title: "Project Board",
		sublabel: "NPD kanban & project chat",
		href: "/board",
		roles: ["Projects User", "Projects Manager", "HR Manager", "System Manager"],
	},
]

// The rows this user may be offered. `userRoles` is `get_current_user_info().roles`
// — the server's own `frappe.get_roles()`, so the PWA never assembles its own
// idea of who someone is.
//
// Anything that is not an array of strings yields an empty list rather than
// throwing: userResource.data is undefined on first paint, and a nav that
// crashes before the session lands is worse than a nav briefly missing two
// optional rows. It fails CLOSED — an unknown user is offered nothing.
export function visibleAppLinks(userRoles) {
	if (!Array.isArray(userRoles)) return []
	const held = new Set(userRoles)
	return APP_LINKS.filter((link) => link.roles.some((role) => held.has(role)))
}

// A same-origin path only. Anything that could name a host (`//evil`, a
// scheme) is rejected so a future edit to APP_LINKS cannot turn a nav row
// into an open redirect.
export function isSameOriginPath(href) {
	return typeof href === "string" && /^\/(?!\/)/.test(href) && !/[\s\\]/.test(href)
}
