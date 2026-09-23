const routes = [
	{
		name: "OTRequestListView",
		path: "/ot-requests",
		component: () => import("@/views/ot/OTRequestList.vue"),
	},
	{
		name: "OTRequestFormView",
		path: "/ot-requests/new",
		component: () => import("@/views/ot/OTRequestForm.vue"),
	},
	{
		name: "OTRequestDetailView",
		path: "/ot-requests/:id",
		props: true,
		component: () => import("@/views/ot/OTRequestForm.vue"),
	},
	{
		// HR policy, 23 Sep 2026: no banked overtime, so no bank, converter or
		// replacement-leave claim screens. Saved links land on Requests.
		path: "/replacement-leave/:rest(.*)*",
		redirect: "/requests",
	},
]

export default routes
