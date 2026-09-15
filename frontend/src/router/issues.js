// the Issues LIST/BOARD lives in the merged Helpdesk page (router/index.js,
// HelpdeskHub.vue → IssuesTab.vue switches board vs personal list by role —
// server row scope is the real protection); only form + detail render in the
// FormShell. The legacy v15.105.0 alias redirects from router/helpdeskHub.js.
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
]

export default routes
