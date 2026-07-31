import { markRaw } from "vue"

import HomeIcon from "@/components/icons/HomeIcon.vue"
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"
import KPIIcon from "@/components/icons/KPIIcon.vue"

// Single source of truth for primary navigation, consumed by both shells
// (BottomTabs on phone, SideNav on lg+). `title` and `shortTitle` are i18n
// source strings — consumers must wrap them with the injected $translate.
// `shortTitle` is the design's compact tab-bar label (fits 6 tabs on phones).
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
]
