import { HR_TAB, HUB_PATH, IT_TAB } from "@/utils/helpdeskHub"

// The two old list routes and their legacy alias. Each keeps working as a
// redirect into the merged page with the pill that used to be that page —
// nothing a notification, bookmark or the v15.105.0 quick link produced can
// 404. Registered inside the tab shell (router/index.js) next to the hub.
// Vue-free on purpose: router/__tests__/helpdesk-hub-routes.test.js resolves
// these with a real vue-router instance.
const routes = [
	{ path: "/issues", redirect: { path: HUB_PATH, query: { tab: HR_TAB } } },
	{ path: "/hr/issues", redirect: { path: HUB_PATH, query: { tab: HR_TAB } } },
	{ path: "/helpdesk", redirect: { path: HUB_PATH, query: { tab: IT_TAB } } },
]

export default routes
