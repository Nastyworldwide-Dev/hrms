import { markRaw } from "vue"

import HomeIcon from "@/components/icons/HomeIcon.vue"
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"
import KPIIcon from "@/components/icons/KPIIcon.vue"
import SupportIcon from "@/components/icons/SupportIcon.vue"
import SopIcon from "@/components/icons/SopIcon.vue"
import MoreIcon from "@/components/icons/MoreIcon.vue"
import HelpdeskIcon from "@/components/icons/HelpdeskIcon.vue"
import ApprovaIcon from "@/components/icons/ApprovaIcon.vue"
import ProjectBoardIcon from "@/components/icons/ProjectBoardIcon.vue"
import { APP_LINKS, visibleAppLinks } from "@/data/appLinks"

// Single source of truth for primary navigation, consumed by both shells
// (BottomTabs on phone, SideNav on lg+). `title` and `shortTitle` are i18n
// source strings — consumers must wrap them with the injected $translate.
// `shortTitle` is the design's compact tab-bar label. The phone bar shows
// TAB_ITEMS (5 primaries + More); SideNav shows the full NAV_ITEMS list.
export const NAV_ITEMS = [
	{ icon: markRaw(HomeIcon), title: "Home", shortTitle: "Home", route: "/home" },
	{
		icon: markRaw(AttendanceIcon),
		title: "Attendance",
		shortTitle: "Attend",
		route: "/dashboard/attendance",
	},
	{
		icon: markRaw(LeaveIcon),
		title: "Leaves",
		shortTitle: "Leaves",
		route: "/dashboard/leaves",
	},
	{
		icon: markRaw(ExpenseIcon),
		title: "Expenses",
		shortTitle: "Expenses",
		route: "/dashboard/expense-claims",
	},
	{
		icon: markRaw(KPIIcon),
		title: "KPI",
		shortTitle: "KPI",
		route: "/dashboard/kpi",
	},
	{
		icon: markRaw(SupportIcon),
		title: "Issues",
		shortTitle: "Issues",
		route: "/issues",
	},
	{
		icon: markRaw(SopIcon),
		title: "SOPs",
		shortTitle: "SOPs",
		route: "/sop",
	},
]

// Native Helpdesk (v16.23.0): a router destination, not an Apps link-out.
// More and SideNav append it only once data/helpdesk.js confirms the app is
// installed on this site — same gate pattern as Team.
export const HELPDESK_ITEM = {
	icon: markRaw(HelpdeskIcon),
	title: "Helpdesk",
	shortTitle: "Helpdesk",
	route: "/helpdesk",
}

// Phone tab bar — FIVE fixed destinations (spec §13.1, §10.1 #8). A bar whose
// destinations change under the user breaks Ionic's per-tab navigation stacks,
// which is why the count is fixed rather than "whatever fits".
//
// §13.1 recommends HOME · ATTEND · LEAVE · PAY · MORE. There is no Pay screen
// in this app — no salary-slip route exists, and building one is a new feature
// (§1, out of scope) — so Expenses takes the fourth slot. Flagged for P&C:
// DECISION 2 is not signed off, and the PAY substitution is part of what needs
// confirming.
//
// `routes` lists every path a tab claims for its active state.
export const TAB_ITEMS = [
	NAV_ITEMS[0], // Home
	NAV_ITEMS[1], // Attendance
	NAV_ITEMS[2], // Leaves
	NAV_ITEMS[3], // Expenses — stands in for §13.1's PAY
	{
		icon: markRaw(MoreIcon),
		title: "More",
		shortTitle: "More",
		route: "/more",
		routes: [
			"/more",
			"/dashboard/kpi",
			"/issues",
			"/sop",
			"/team",
			"/remote-approvals",
			"/helpdesk",
		],
	},
]

// Everything not in the tab bar (§13.1): KPI, Issues, SOPs — plus Team and
// Remote Approvals, which the More screen adds conditionally.
export const MORE_ITEMS = NAV_ITEMS.slice(4)

// Sibling apps reached by leaving the PWA (see data/appLinks.js). Rendered as
// their own "Apps" group under More and below the SideNav divider; never in the
// phone tab bar, whose five destinations are fixed.
const APP_ICONS = {
	approva: markRaw(ApprovaIcon),
	board: markRaw(ProjectBoardIcon),
}
export const APP_ITEMS = APP_LINKS.map((link) => ({ ...link, icon: APP_ICONS[link.key] }))

// The rows this user may be offered, icons attached. Both shells (More on the
// phone, SideNav on lg+) render the same list, so the allowlist is applied
// once here rather than twice in the views — the two cannot drift apart.
// Pass `get_current_user_info().roles`; an absent payload yields [].
export const visibleAppItems = (userRoles) =>
	visibleAppLinks(userRoles).map((link) => ({ ...link, icon: APP_ICONS[link.key] }))
