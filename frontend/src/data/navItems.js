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

// Phone tab bar: the last two NAV_ITEMS (Issues, SOPs) live under More.
// `routes` lists every path the More tab claims for its active state.
export const TAB_ITEMS = [
	...NAV_ITEMS.slice(0, 5),
	{
		icon: markRaw(MoreIcon),
		title: "More",
		shortTitle: "More",
		route: "/more",
		routes: ["/more", "/issues", "/sop"],
	},
]

export const MORE_ITEMS = NAV_ITEMS.slice(5)
