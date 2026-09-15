import { markRaw } from "vue"

import HomeIcon from "@/components/icons/HomeIcon.vue"
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"
import KPIIcon from "@/components/icons/KPIIcon.vue"
import SopIcon from "@/components/icons/SopIcon.vue"
import MoreIcon from "@/components/icons/MoreIcon.vue"
import HelpdeskIcon from "@/components/icons/HelpdeskIcon.vue"
import ApprovaIcon from "@/components/icons/ApprovaIcon.vue"
import ProjectBoardIcon from "@/components/icons/ProjectBoardIcon.vue"
import { visibleAppLinks } from "@/data/appLinks"
import { HUB_PATH } from "@/utils/helpdeskHub"

// Single source of truth for primary navigation, consumed by both shells
// (BottomTabs on phone, SideNav on lg+). `title` and `shortTitle` are i18n
// source strings — consumers must wrap them with the injected $translate.
// `shortTitle` is the design's compact tab-bar label. The phone bar shows
// TAB_ITEMS (5 primaries + More); SideNav shows the full NAV_ITEMS list.
const NAV_ITEMS = [
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
		// ONE entry for Issues + Helpdesk (owner, 15 Sep 2026), in the slot
		// Issues held. HR Issues is for everyone, so the entry is never gated;
		// the IT pill inside is what hides on sites without the Helpdesk app.
		icon: markRaw(HelpdeskIcon),
		title: "Helpdesk",
		shortTitle: "Helpdesk",
		route: HUB_PATH,
	},
	{
		icon: markRaw(SopIcon),
		title: "SOPs",
		shortTitle: "SOPs",
		route: "/sop",
	},
]

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
		routes: ["/more", "/dashboard/kpi", HUB_PATH, "/sop", "/team", "/remote-approvals"],
	},
]

// Everything not in the tab bar (§13.1): KPI, Helpdesk, SOPs — plus Team and
// Remote Approvals, which the More screen adds conditionally.
export const MORE_ITEMS = NAV_ITEMS.slice(4)

// Sibling apps reached by leaving the PWA (see data/appLinks.js). Rendered as
// their own "Apps" group under More and below the SideNav divider; never in the
// phone tab bar, whose five destinations are fixed.
const APP_ICONS = {
	approva: markRaw(ApprovaIcon),
	board: markRaw(ProjectBoardIcon),
}

// The rows this user may be offered, icons attached. Both shells (More on the
// phone, SideNav on lg+) render the same list, so the allowlist is applied
// once here rather than twice in the views — the two cannot drift apart.
// Pass `get_current_user_info().roles`; an absent payload yields [].
export const visibleAppItems = (userRoles) =>
	visibleAppLinks(userRoles).map((link) => ({ ...link, icon: APP_ICONS[link.key] }))
