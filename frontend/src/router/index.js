import { createRouter, createWebHistory } from "@ionic/vue-router"

import TabbedView from "@/views/TabbedView.vue"
import attendanceRoutes from "./attendance"
import otRoutes from "./ot"
import leaveRoutes from "./leaves"
import claimRoutes from "./claims"
import issueRoutes from "./issues"
import sopRoutes from "./sop"

const routes = [
	{
		path: "/",
		redirect: "/home",
	},
	{
		path: "/",
		component: TabbedView,
		children: [
			{
				path: "",
				redirect: "/home",
			},
			{
				path: "/home",
				name: "Home",
				component: () => import("@/views/Home.vue"),
			},
			{
				path: "/dashboard/attendance",
				name: "AttendanceDashboard",
				component: () => import("@/views/attendance/Dashboard.vue"),
			},
			{
				path: "/dashboard/leaves",
				name: "LeavesDashboard",
				component: () => import("@/views/leave/Dashboard.vue"),
			},
			{
				path: "/dashboard/expense-claims",
				name: "ExpenseClaimsDashboard",
				component: () => import("@/views/expense_claim/Dashboard.vue"),
			},
			{
				path: "/dashboard/kpi",
				name: "KPIDashboard",
				component: () => import("@/views/kpi/Dashboard.vue"),
			},
			{
				// lives in the tab shell (bottom tabs / side nav stay visible);
				// renders the HR board or the personal list depending on role
				path: "/issues",
				name: "EmployeeIssueListView",
				component: () => import("@/views/issues/IssuesTab.vue"),
			},
			{
				// SOP library tab: one list for everyone, HR additionally gets
				// every department group, drafts and the authoring sheet
				path: "/sop",
				name: "SopListView",
				component: () => import("@/views/sop/SopList.vue"),
			},
			{
				// manager day view; reached via More, server returns empty
				// for users without direct reports
				path: "/team",
				name: "TeamView",
				component: () => import("@/views/team/TeamDashboard.vue"),
			},
			{
				// overflow hub for the phone tab bar (Issues, SOPs, Team)
				path: "/more",
				name: "MoreView",
				component: () => import("@/views/More.vue"),
			},
		],
	},
	{
		path: "/login",
		name: "Login",
		component: () => import("@/views/Login.vue"),
	},
	{
		path: "/forgot-password",
		name: "ForgotPassword",
		component: () => import("@/views/ForgotPassword.vue"),
	},
	{
		path: "/profile",
		name: "Profile",
		component: () => import("@/views/Profile.vue"),
	},
	{
		path: "/notifications",
		name: "Notifications",
		component: () => import("@/views/Notifications.vue"),
	},
	{
		path: "/settings",
		name: "Settings",
		component: () => import("@/views/AppSettings.vue"),
	},
	{
		path: "/change-password",
		name: "ChangePassword",
		component: () => import("@/views/ChangePassword.vue"),
	},
	{
		path: "/hr-contacts",
		name: "HRContacts",
		component: () => import("@/views/HRContacts.vue"),
	},
	{
		path: "/remote-approvals",
		name: "RemoteApprovals",
		component: () => import("@/views/RemoteApprovals.vue"),
	},
	{
		path: "/invalid-employee",
		name: "InvalidEmployee",
		component: () => import("@/views/InvalidEmployee.vue"),
	},
	{
		path: "/",
		component: () => import("@/views/FormShell.vue"),
		children: [
			...attendanceRoutes,
			...otRoutes,
			...leaveRoutes,
			...claimRoutes,
			...issueRoutes,
			...sopRoutes,
		],
	},
]

const router = createRouter({
	history: createWebHistory("/hrms"),
	routes,
})

export default router
