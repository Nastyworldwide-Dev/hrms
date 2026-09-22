<template>
	<div class="w-full">
		<div class="g-eyebrow mb-4">
			{{ __("Requests") }}
		</div>
		<GSegmented :buttons="TAB_BUTTONS" v-model="activeTab" :label="__('Requests')" />
		<p v-if="refreshing" class="text-xs text-ink-500 mt-2" role="status">
			{{ __("Refreshing…") }}
		</p>
		<RequestList v-if="activeTab == 'My Requests'" :items="shown" />
		<RequestList v-else-if="activeTab == 'Team Requests'" :items="shown" :teamRequests="true" />
		<RequestList v-else-if="activeTab == 'History'" :items="shown" :teamRequests="true" />

		<!-- Not a GGhostButton: that is a glass surface and Home already spends
		     4 of its 6 (§15.1). A text control under a list costs none, and the
		     row it reveals is the one the person came for. -->
		<button
			v-if="hidden > 0"
			type="button"
			class="g-focusable w-full py-3 text-sm text-ink-600 bg-transparent border-none"
			@click="showAll = true"
		>
			{{ __("Show {0} more", [hidden]) }}
		</button>
	</div>
</template>

<script setup>
import { ref, inject, onMounted, computed, markRaw, watch } from "vue"

import GSegmented from "@/components/glass/GSegmented.vue"
import RequestList from "@/components/RequestList.vue"

import {
	historyShiftRequests,
	myAttendanceRequests,
	myShiftRequests,
	teamShiftRequests,
	teamAttendanceRequests,
} from "@/data/attendance"
import { historyClaims, myClaims, teamClaims } from "@/data/claims"
import { historyLeaves, myLeaves, teamLeaves } from "@/data/leaves"
import { isApprover } from "@/data/team"
import {
	myOTRequests,
	teamOTRequests,
	myReplacementLeaveClaims,
	teamReplacementLeaveClaims,
} from "@/data/overtime"

import AttendanceRequestItem from "@/components/AttendanceRequestItem.vue"
import ExpenseClaimItem from "@/components/ExpenseClaimItem.vue"
import LeaveRequestItem from "@/components/LeaveRequestItem.vue"
import ShiftRequestItem from "@/components/ShiftRequestItem.vue"
import OTRequestItem from "@/components/OTRequestItem.vue"
import ReplacementLeaveClaimItem from "@/components/ReplacementLeaveClaimItem.vue"

import { useListUpdate, useReloadOnGap } from "@/composables/realtime"
import {
	MY_REQUEST_LISTS,
	REQUEST_LISTS,
	TEAM_REQUEST_LISTS,
	reloadLists,
	reloadRequestLists,
} from "@/data/requestLists"
import { siteTime } from "@/utils/siteTime"

const activeTab = ref("My Requests")

// Home shows the first five of whatever the active tab holds, and a control
// that reveals the rest in place. The fold is a budget, not a length
// (home-fold-budget.test.js): the ANCHOR above this panel fits the smallest
// usable height and this list is scrolled to by design — what the cap removes
// is an UNBOUNDED scroll, not the scroll. A row is two lines plus py-3 either
// side, ~62px, so five is ~310px inside a ~440px small-phone budget.
//
// Expanding, not linking: each tab merges SIX doctypes and there is no
// combined list route, so "See all (9)" could only point at one type's screen
// and answer a tap about nine requests with a page showing three.
const HOME_ROWS = 5
const showAll = ref(false)
const socket = inject("$socket")
const __ = inject("$translate")

// Team tabs only for people approval work can actually route to — everyone
// else got a permanently empty "Team Requests" tab before this gate.
// __("My Requests"), __("Team Requests"), __("History")
const TAB_BUTTONS = computed(() =>
	isApprover.data ? ["My Requests", "Team Requests", "History"] : ["My Requests"]
)

// The cached isApprover verdict hydrates async and can flip true -> false
// after paint; without this clamp a user parked on a vanished tab renders an
// empty panel (no v-if branch matches).
watch(TAB_BUTTONS, (tabs) => {
	if (!tabs.includes(activeTab.value)) {
		console.info("[RequestPanel] active tab vanished, falling back:", activeTab.value)
		activeTab.value = "My Requests"
	}
})

// A cached (IndexedDB) paint can show last session's status until the first
// fetch of this session answers; say so instead of painting it as current.
const refreshing = computed(() =>
	(activeTab.value == "My Requests" ? MY_REQUEST_LISTS : TEAM_REQUEST_LISTS).some(
		(list) => !list.fetched && !list.error
	)
)

const myRequests = computed(() =>
	updateRequestDetails(
		myLeaves,
		myClaims,
		myShiftRequests,
		myAttendanceRequests,
		myOTRequests,
		myReplacementLeaveClaims
	)
)

const teamRequests = computed(() =>
	updateRequestDetails(
		teamLeaves,
		teamClaims,
		teamShiftRequests,
		teamAttendanceRequests,
		teamOTRequests,
		teamReplacementLeaveClaims
	)
)

// Attendance Request, OT Request and Replacement Leave Claim are all
// docstatus-driven (no status/approver field), so the history trail — which is
// "decided, and I was the named approver" — covers leaves, claims and shift
// requests only.
const historyRequests = computed(() =>
	updateRequestDetails(historyLeaves, historyClaims, historyShiftRequests, null, null, null)
)

const activeRequests = computed(() => {
	if (activeTab.value === "Team Requests") return teamRequests.value
	if (activeTab.value === "History") return historyRequests.value
	return myRequests.value
})

const shown = computed(() =>
	showAll.value ? activeRequests.value : activeRequests.value.slice(0, HOME_ROWS)
)

// What is HIDDEN, not what exists: a person with seven requests told "Show 7
// more" taps it and finds two new rows.
const hidden = computed(() =>
	showAll.value ? 0 : Math.max(0, activeRequests.value.length - HOME_ROWS)
)

// The tab strip swaps the list under the control. A stale `showAll` would open
// the next tab already expanded, which is the opposite of what the cap is for.
watch(activeTab, () => {
	showAll.value = false
})

function updateRequestDetails(
	leaves,
	claims,
	shiftRequests,
	attendanceRequests,
	otRequests,
	replacementLeaveClaims
) {
	const requests = [
		leaves,
		claims,
		shiftRequests,
		attendanceRequests,
		otRequests,
		replacementLeaveClaims,
	].reduce((acc, resource) => acc.concat(resource?.data || []), [])

	const componentMap = {
		"Leave Application": LeaveRequestItem,
		"Expense Claim": ExpenseClaimItem,
		"Shift Request": ShiftRequestItem,
		"Attendance Request": AttendanceRequestItem,
		"OT Request": OTRequestItem,
		"Replacement Leave Claim": ReplacementLeaveClaimItem,
	}
	requests.forEach((request) => {
		request.component = markRaw(componentMap[request.doctype])
	})

	return getSortedRequests(requests)
}

function getSortedRequests(list) {
	// return top 10 requests sorted by posting date
	return list
		.sort((a, b) => {
			// site-clock strings; the Date constructor rejects them on Safari (I-F3)
			return siteTime(b.creation).valueOf() - siteTime(a.creation).valueOf()
		})
		.splice(0, 10)
}

onMounted(() => {
	// Every list_update reloads the employee's own list too: the server pushes
	// hrms:refetch_resource for `my_*` only while the socket is alive, and a
	// list_update is the one event the room replays after a rejoin.
	for (const [doctype, lists] of Object.entries(REQUEST_LISTS)) {
		useListUpdate(socket, doctype, () => reloadLists([lists.my, ...lists.team], doctype))
	}
	useReloadOnGap(reloadRequestLists)
	reloadRequestLists("mount")
})
</script>
