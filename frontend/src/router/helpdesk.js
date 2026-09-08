// Native Helpdesk (v16.23.0). The LIST lives in the tab shell (router/index.js)
// so bottom tabs / side nav stay visible; raise + detail render in the
// FormShell like every other form page.
const routes = [
	{
		name: "HelpdeskTicketNew",
		path: "/helpdesk/new",
		component: () => import("@/views/helpdesk/TicketNew.vue"),
	},
	{
		name: "HelpdeskTicketDetail",
		path: "/helpdesk/:id",
		props: true,
		component: () => import("@/views/helpdesk/TicketDetail.vue"),
	},
]

export default routes
