// the SOP LIST route lives in router/index.js under TabbedView (it is a
// primary tab — bottom tabs / side nav stay visible); only the reading view
// renders in the FormShell so the back button returns to the list
const routes = [
	{
		name: "SopDetailView",
		path: "/sop/:id",
		props: true,
		component: () => import("@/views/sop/SopDetail.vue"),
	},
]

export default routes
