import { userResource } from "@/data/user"

const HR_BOARD_ROLES = ["HR User", "HR Manager", "System Manager"]

// router.beforeEach reloads userResource before any guarded route resolves,
// so roles are present here; fail toward Home if not
const requireHRRole = (to, from, next) => {
	const roles = userResource.data?.roles || []
	if (roles.some((role) => HR_BOARD_ROLES.includes(role))) {
		next()
	} else {
		console.warn("[issues] blocked non-HR user from HR issue board")
		next({ name: "Home" })
	}
}

// the My Issues LIST route lives in router/index.js under TabbedView so the
// tab shell stays visible; only form/detail/board render in the FormShell
const routes = [
	{
		name: "EmployeeIssueFormView",
		path: "/issues/new",
		component: () => import("@/views/issues/IssueForm.vue"),
	},
	{
		name: "EmployeeIssueDetailView",
		path: "/issues/:id",
		props: true,
		component: () => import("@/views/issues/IssueForm.vue"),
	},
	{
		name: "HRIssueBoard",
		path: "/hr/issues",
		beforeEnter: requireHRRole,
		component: () => import("@/views/issues/HRIssueBoard.vue"),
	},
]

export default routes
