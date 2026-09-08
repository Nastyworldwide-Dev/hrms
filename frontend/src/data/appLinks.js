// Sibling Frappe apps that live on the same site as the HRMS PWA and are
// reached by leaving it: Helpdesk (/helpdesk), Approva (/approva) and Project
// Board (/board) each ship their own SPA under their own PWA scope, so vue-
// router cannot reach them — the row does a full navigation via `href`, not a
// `route`. Same origin means the Frappe session cookie carries over and the
// target opens signed in.
//
// Kept free of Vue imports so the data can be unit-tested under node; icons
// are attached in navItems.js (APP_ITEMS).
//
// `title` and `sublabel` are i18n source strings — wrap with $translate.
export const APP_LINKS = [
	{
		key: "helpdesk",
		title: "Helpdesk",
		sublabel: "Raise and track IT & admin tickets",
		// the customer portal, not the agent desk (/helpdesk/tickets)
		href: "/helpdesk/my-tickets",
	},
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

// A same-origin path only. Anything that could name a host (`//evil`, a
// scheme) is rejected so a future edit to APP_LINKS cannot turn a nav row
// into an open redirect.
export function isSameOriginPath(href) {
	return typeof href === "string" && /^\/(?!\/)/.test(href) && !/[\s\\]/.test(href)
}
