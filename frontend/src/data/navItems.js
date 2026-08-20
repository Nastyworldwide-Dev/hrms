import { markRaw } from "vue"

import HomeIcon from "@/components/icons/HomeIcon.vue"
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"
import KPIIcon from "@/components/icons/KPIIcon.vue"
import SupportIcon from "@/components/icons/SupportIcon.vue"
import SopIcon from "@/components/icons/SopIcon.vue"
import MoreIcon from "@/components/icons/MoreIcon.vue"

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
		title: "My KPI",
		shortTitle: "My KPI",
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
		routes: ["/more", "/dashboard/kpi", "/issues", "/sop", "/team", "/remote-approvals"],
	},
]

// Everything not in the tab bar (§13.1): KPI, Issues, SOPs — plus Team and
// Remote Approvals, which the More screen adds conditionally.
export const MORE_ITEMS = NAV_ITEMS.slice(4)
