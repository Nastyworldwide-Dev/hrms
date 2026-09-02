import { createRouter, createWebHistory } from "@ionic/vue-router"

import TabbedView from "@/views/TabbedView.vue"
import attendanceRoutes from "./attendance"
import claimRoutes from "./claims"
import issueRoutes from "./issues"
import leaveRoutes from "./leaves"
import otRoutes from "./ot"
import sopRoutes from "./sop"
import { isStaleChunkError } from "./stale-chunk"

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
				// leader roster grid; server fences to the caller's own reports,
				// so a user without a team sees an empty roster
				path: "/team/roster",
				name: "TeamRosterView",
				component: () => import("@/views/team/TeamRoster.vue"),
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

// Glass specimen route (spec §16.4) — dev bundle only; the guard is statically
// replaced, so production builds drop the route and the chunk entirely
if (import.meta.env.DEV) {
	routes.push({
		path: "/design",
		name: "DesignSpecimen",
		component: () => import("@/views/DesignSpecimen.vue"),
	})
}

// Catch-all, LAST — it must be pushed after the dev-only /design route above,
// or /design would match this in dev instead of the specimen. Without it any
// unknown URL rendered a blank page with no message and no way back (8.13).
routes.push({
	path: "/:pathMatch(.*)*",
	name: "NotFound",
	component: () => import("@/views/NotFound.vue"),
})

const router = createRouter({
	history: createWebHistory("/hrms"),
	routes,
})

// Release focus before every navigation. Ionic keeps the outgoing page mounted
// and stamps it aria-hidden — but the control that triggered the navigation
// still holds focus inside it, so the browser reports on every push:
//
//   Blocked aria-hidden on an element because its descendant retained focus.
//   Element with focus: <button.g-row g-row--tappable>
//   Ancestor with aria-hidden: <div class="ion-page g-page ion-page-hidden">
//
// A focus trapped in a hidden page is unreachable to assistive tech and to the
// keyboard path (focus resumes inside a page that no longer exists visually).
// One blur here covers every route, instead of per-page lifecycle handlers.
router.beforeEach(() => {
	document.activeElement?.blur?.()
})

// After a deploy a still-open tab can lazy-load a chunk hash the service worker
// has already purged; the dynamic import rejects mid-navigation. Recover by
// doing a full reload once, which boots index.html into the current build. The
// sessionStorage latch stops a genuinely-broken chunk (gone for a reason other
// than a deploy) from reload-looping. See stale-chunk.js for the predicate.
router.onError((err) => {
	if (!isStaleChunkError(err?.message)) return
	const KEY = "hrms:chunk-reloaded"
	if (sessionStorage.getItem(KEY)) return
	console.warn("[Router] stale chunk after deploy — reloading into current build:", err?.message)
	try {
		sessionStorage.setItem(KEY, "1")
	} catch (e) {
		// private mode / storage disabled: reload anyway, worst case is a loop
		// the user breaks by closing the tab — still better than a dead route
	}
	window.location.reload()
})

// A clean navigation means the current build loaded — clear the latch so a
// future deploy can recover again.
router.afterEach(() => {
	try {
		sessionStorage.removeItem("hrms:chunk-reloaded")
	} catch (e) {
		// storage unavailable — nothing to clear
	}
})

export default router
