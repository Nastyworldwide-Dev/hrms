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
		name: "ReplacementLeaveView",
		path: "/replacement-leave",
		component: () => import("@/views/ot/ReplacementLeave.vue"),
	},
	{
		name: "ReplacementLeaveClaimFormView",
		path: "/replacement-leave/claims/new",
		component: () => import("@/views/ot/ReplacementLeaveClaimForm.vue"),
	},
	{
		name: "ReplacementLeaveClaimDetailView",
		path: "/replacement-leave/claims/:id",
		props: true,
		component: () => import("@/views/ot/ReplacementLeaveClaimForm.vue"),
	},
]

export default routes
