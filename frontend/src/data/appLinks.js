// Sibling Frappe apps that live on the same site as the HRMS PWA and are
// reached by leaving it: Approva (/approva) and Project Board (/board).
// Helpdesk left this list in v16.23.0 — it has a native front end now
// (the IT Helpdesk pill of views/helpdesk/HelpdeskHub.vue). Both apps each ship their own SPA under their own PWA scope, so vue-
// router cannot reach them — the row does a full navigation via `href`, not a
// `route`. Same origin means the Frappe session cookie carries over and the
// target opens signed in.
//
// Kept free of Vue imports so the data can be unit-tested under node; icons
// are attached in navItems.js (visibleAppItems).
//
// `title` and `sublabel` are i18n source strings — wrap with $translate.
// WHETHER a row is offered is the server's answer (audit F-15: no role names
// in the frontend): hrms.api.app_links.get_my_apps returns the keys this
// person may be offered, and the role rule lives there. Offering is not
// access control; each app enforces its own permissions on the far side.

export const APP_LINKS = [
	{
		key: "approva",
		title: "Approva",
		sublabel: "Purchase requests & approvals",
		href: "/approva",
	},
	{
		key: "board",
		title: "Project Board",
		sublabel: "NPD kanban & project chat",
		href: "/board",
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
export function visibleAppLinks(offeredKeys) {
	if (!Array.isArray(offeredKeys)) return []
	const offered = new Set(offeredKeys)
	return APP_LINKS.filter((link) => offered.has(link.key))
}

// A same-origin path only. Anything that could name a host (`//evil`, a
// scheme) is rejected so a future edit to APP_LINKS cannot turn a nav row
// into an open redirect.
export function isSameOriginPath(href) {
	return typeof href === "string" && /^\/(?!\/)/.test(href) && !/[\s\\]/.test(href)
}
