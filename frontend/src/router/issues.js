// the Issues LIST/BOARD tab route lives in router/index.js under TabbedView
// (IssuesTab.vue switches board vs personal list by role — server row scope
// is the real protection); only form + detail render in the FormShell
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
		// legacy deep links from the v15.105.0 quick link
		path: "/hr/issues",
		redirect: "/issues",
	},
]

export default routes
