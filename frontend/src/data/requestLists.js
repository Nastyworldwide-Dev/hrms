// The one map of request doctype -> the Home panel lists it feeds. Every
// non-socket refresh path (mount, pull-to-refresh, reconnect, long-hidden
// resume) reloads through here, so a decided request reaches the employee's
// Home even when the socket was dead at the moment of the decision (A-C1,
// 21 Sep 2026). tests/audit/request-lists-reload.test.mjs pins that every
// `hrms:my_*` resource is listed.
import {
	historyShiftRequests,
	myAttendanceRequests,
	myShiftRequests,
	teamAttendanceRequests,
	teamShiftRequests,
} from "@/data/attendance"
import { historyClaims, myClaims, teamClaims } from "@/data/claims"
import { historyLeaves, myLeaves, teamLeaves } from "@/data/leaves"
import {
	myOTRequests,
	myReplacementLeaveClaims,
	teamOTRequests,
	teamReplacementLeaveClaims,
} from "@/data/overtime"

export const REQUEST_LISTS = {
	"Leave Application": { my: myLeaves, team: [teamLeaves, historyLeaves] },
	"Expense Claim": { my: myClaims, team: [teamClaims, historyClaims] },
	"Shift Request": { my: myShiftRequests, team: [teamShiftRequests, historyShiftRequests] },
	"Attendance Request": { my: myAttendanceRequests, team: [teamAttendanceRequests] },
	"OT Request": { my: myOTRequests, team: [teamOTRequests] },
	"Replacement Leave Claim": { my: myReplacementLeaveClaims, team: [teamReplacementLeaveClaims] },
}

export const MY_REQUEST_LISTS = Object.values(REQUEST_LISTS).map((lists) => lists.my)
export const TEAM_REQUEST_LISTS = Object.values(REQUEST_LISTS).flatMap((lists) => lists.team)

// A list already in flight is left alone (the cold-start auto fetch is usually
// still running when the panel mounts). Resolves when every reload settled.
export function reloadLists(lists, why) {
	const idle = lists.filter((list) => !list.loading)
	console.info("[requestLists] reload (%s): %d of %d lists", why, idle.length, lists.length)
	return Promise.allSettled(idle.map((list) => list.reload()))
}

export const reloadRequestLists = (why) =>
	reloadLists([...MY_REQUEST_LISTS, ...TEAM_REQUEST_LISTS], why)
