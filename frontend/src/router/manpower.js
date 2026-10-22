// Lazy chunks: the wizard and the detail page are not in the first download.
const routes = [
	{
		name: "ManpowerRequestListView",
		path: "/manpower-requests",
		component: () => import("@/views/manpower/ManpowerRequestList.vue"),
	},
	{
		name: "ManpowerRequestFormView",
		path: "/manpower-requests/new",
		component: () => import("@/views/manpower/ManpowerRequestWizard.vue"),
	},
	{
		name: "ManpowerRequestDetailView",
		path: "/manpower-requests/:id",
		props: true,
		component: () => import("@/views/manpower/ManpowerRequestDetail.vue"),
	},
]

export default routes
