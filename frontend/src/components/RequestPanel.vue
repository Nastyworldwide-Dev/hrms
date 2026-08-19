<template>
	<div class="w-full">
		<div
			class="hidden lg:block font-sans font-extrabold text-[10px] tracking-[0.1em] uppercase text-ink-600 mb-4"
		>
			{{ __("Requests") }}
		</div>
		<TabButtons :buttons="TAB_BUTTONS" v-model="activeTab" />
		<RequestList v-if="activeTab == 'My Requests'" :items="myRequests" />
		<RequestList
			v-else-if="activeTab == 'Team Requests'"
			:items="teamRequests"
			:teamRequests="true"
		/>
		<RequestList
			v-else-if="activeTab == 'History'"
			:items="historyRequests"
			:teamRequests="true"
		/>
	</div>
</template>

<script setup>
import { ref, inject, onMounted, computed, markRaw } from "vue"

import TabButtons from "@/components/TabButtons.vue"
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

import { useListUpdate } from "@/composables/realtime"

const activeTab = ref("My Requests")
const socket = inject("$socket")
const __ = inject("$translate")

// Team tabs only for people approval work can actually route to — everyone
// else got a permanently empty "Team Requests" tab before this gate.
// __("My Requests"), __("Team Requests"), __("History")
const TAB_BUTTONS = computed(() =>
	isApprover.data ? ["My Requests", "Team Requests", "History"] : ["My Requests"]
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
			return new Date(b.creation) - new Date(a.creation)
		})
		.splice(0, 10)
}

onMounted(() => {
	useListUpdate(socket, "Leave Application", () => {
		teamLeaves.reload()
		historyLeaves.reload()
	})
	useListUpdate(socket, "Expense Claim", () => {
		teamClaims.reload()
		historyClaims.reload()
	})
	useListUpdate(socket, "Shift Request", () => {
		teamShiftRequests.reload()
		historyShiftRequests.reload()
	})
	useListUpdate(socket, "Attendance Request", () => teamAttendanceRequests.reload())
	useListUpdate(socket, "OT Request", () => teamOTRequests.reload())
	useListUpdate(socket, "Replacement Leave Claim", () => teamReplacementLeaveClaims.reload())
})
</script>
