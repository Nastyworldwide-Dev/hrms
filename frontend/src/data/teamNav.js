// "Your team" — what a leader does for others (alpha.14 O): Manpower requests
// (HR), Approvals, Team, Roster, Organizational Chart. ONE list, read by the
// phone's More screen AND the laptop SideNav. It used to live inside More.vue
// alone, so every row added here after the side nav was built (Approvals,
// Roster, Manpower requests, Organizational Chart) never reached a laptop —
// owner, 2 Nov 2026: "why does Nadi on laptop not have More".
//
// Each row appears only when the server says it applies:
// isApprover (anyone something is routed to), hasTeam (direct reports, or HR),
// hasCompanyView (an Attendance Report Viewer: Team only, never Roster),
// is_hr (the Manpower requests board).
import { CalendarRange, ClipboardList, Network, SquareCheck, Users } from "lucide-vue-next"
import { computed, markRaw, onMounted, watch } from "vue"

import { manpowerBoardCount } from "@/data/manpower"
import { needsYouResource } from "@/data/needsYou"
import { hasCompanyView, hasTeam, isApprover } from "@/data/team"
import { userResource } from "@/data/user"
import { hasHRRole } from "@/utils/issueBoard"
import { boardRoute } from "@/utils/manpowerBoard"

/**
 * The "Your team" rows for the signed-in person. Call from a component's setup.
 * Each row: { key, icon, title, to, route, badge? }. `to` is what a router push
 * takes; `route` is the path, for a side nav's active state.
 */
export function useTeamItems(__) {
	//: The Approvals number is everything waiting on you, as Home's Needs you.
	const waitingOnYou = computed(
		() =>
			(Number(needsYouResource.data?.total) || 0) + (Number(needsYouResource.data?.checkins) || 0)
	)
	//: HR only (the server's own is_hr verdict, as the HR Issue Board).
	const isHR = computed(() => hasHRRole(userResource.data))
	onMounted(() => {
		if (isApprover.data) needsYouResource.reload()
	})
	// userResource may still be loading at mount: ask the moment the person is known to be HR
	watch(
		isHR,
		(hr) => {
			if (hr) {
				console.info("[teamNav] HR session: loading the manpower board count")
				manpowerBoardCount.reload()
			}
		},
		{ immediate: true }
	)
	const needsHr = computed(() => Number(manpowerBoardCount.data?.counts?.needs_hr) || 0)

	return computed(() => [
		...(isHR.value
			? [
					{
						key: "staff-requests",
						icon: markRaw(ClipboardList),
						title: __("Manpower requests"),
						to: { name: boardRoute.name },
						route: boardRoute.path,
						badge: needsHr.value ? String(needsHr.value) : "",
					},
			  ]
			: []),
		...(isApprover.data
			? [
					{
						key: "approvals",
						icon: markRaw(SquareCheck),
						title: __("Approvals"),
						to: { name: "Approvals" },
						route: "/approvals",
						badge: waitingOnYou.value ? String(waitingOnYou.value) : "",
					},
			  ]
			: []),
		...(hasTeam.data || hasCompanyView.data
			? [{ key: "team", icon: markRaw(Users), title: __("Team"), route: "/team", to: "/team" }]
			: []),
		...(hasTeam.data
			? [
					{
						key: "roster",
						icon: markRaw(CalendarRange),
						title: __("Roster"),
						route: "/team/roster",
						to: "/team/roster",
					},
			  ]
			: []),
		{
			key: "org-chart",
			icon: markRaw(Network),
			title: __("Organizational Chart"),
			route: "/org-chart",
			to: "/org-chart",
		},
	])
}
