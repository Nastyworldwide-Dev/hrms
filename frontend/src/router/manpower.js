// Lazy chunks: the wizard, the detail page and HR's board are not in the first download.
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
		// HR's monitoring board (More -> Staff requests). Presentation only: the server refuses anyone
		// who is not HR (hrms.api.manpower.hr_board), and the row scope fences the companies.
		name: "ManpowerHRBoardView",
		path: "/hr/manpower-requests",
		component: () => import("@/views/manpower/ManpowerHRBoard.vue"),
	},
	{
		name: "ManpowerRequestDetailView",
		path: "/manpower-requests/:id",
		props: true,
		component: () => import("@/views/manpower/ManpowerRequestDetail.vue"),
	},
]

export default routes
