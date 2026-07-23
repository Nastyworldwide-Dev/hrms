import { markRaw } from "vue"

import HomeIcon from "@/components/icons/HomeIcon.vue"
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"
import SalaryIcon from "@/components/icons/SalaryIcon.vue"
import KPIIcon from "@/components/icons/KPIIcon.vue"

// Single source of truth for primary navigation, consumed by both shells
// (BottomTabs on phone, SideNav on lg+). `title` is an i18n source string —
// consumers must wrap it with the injected $translate.
export const NAV_ITEMS = [
	{ icon: markRaw(HomeIcon), title: "Home", route: "/home" },
	{
		icon: markRaw(AttendanceIcon),
		title: "Attendance",
		route: "/dashboard/attendance",
	},
	{ icon: markRaw(LeaveIcon), title: "Leaves", route: "/dashboard/leaves" },
	{
		icon: markRaw(ExpenseIcon),
		title: "Expenses",
		route: "/dashboard/expense-claims",
	},
	{
		icon: markRaw(SalaryIcon),
		title: "Salary",
		route: "/dashboard/salary-slips",
	},
	{ icon: markRaw(KPIIcon), title: "My KPI", route: "/dashboard/kpi" },
]
