<!--
  Requests — the hub the 2.0 tab bar points at (slice 0.1, UX_PLAN §3.3).

  The app had no such screen. What it is FOR was spread across three places:
  starting a request lived in Home's quick links, watching one lived in Home's
  request panel, and the per-type lists lived on the leave and expense
  dashboards. So "where is my leave application?" had three plausible answers
  and no obvious one.

  This is a COMPOSITION, not new machinery. It renders the two components Home
  already renders, in the order the question is asked — what can I ask for, and
  what did I ask for — and nothing on it is a new data path. The plan's fuller
  hub (balances, assets, trips, a sticky "+ New request") belongs to later
  slices; this is the destination the tab needs, built from what exists.

  Home keeps both components. The tab bar is not a reason to take something off
  Home, and the plan's Home (§3.1) still shows what needs you — the difference
  is that Home no longer has to be the ONLY way to reach a request.
-->
<template>
	<BaseLayout :pageTitle="__('Requests')">
		<template #body>
			<GPullRefresh @refresh="refreshRequests" />
			<div
				class="flex flex-col gap-5 px-4 pt-6 pb-8 w-full max-w-content-column-lg mx-auto lg:p-7"
			>
				<!-- FIRST, above the tiles. §5: the numbers belong where the
				     decision is made, not on the screen that stores them — an
				     employee deciding how much leave to take should not have to
				     remember a figure from another screen. The strip renders
				     nothing when there is nothing to say. -->
				<RequestBalances />
				<!-- ONE button, one type sheet (audit P1-B, prototype + mockup 4): the
				     six-tile grid pushed the list below the fold. -->
				<GButton :label="__('New request')" @click="typeSheetOpen = true" />
				<RequestPanel />
				<GActionSheet
					:is-open="typeSheetOpen"
					:title="__('New request')"
					:actions="requestTypes"
					@select="startRequest"
					@did-dismiss="typeSheetOpen = false"
				/>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { inject, ref } from "vue"
import { useRouter } from "vue-router"

import BaseLayout from "@/components/BaseLayout.vue"
import RequestBalances from "@/components/RequestBalances.vue"
import RequestPanel from "@/components/RequestPanel.vue"
import GActionSheet from "@/components/glass/GActionSheet.vue"
import GButton from "@/components/glass/GButton.vue"
import GPullRefresh from "@/components/glass/GPullRefresh.vue"
import { reloadRequestLists } from "@/data/requestLists"

const __ = inject("$translate")
const router = useRouter()

//: The request types, most used first. Asking HR is not a request (it lives
//: on Help); fixing a day starts from the day, on Calendar (approved Calendar
//: plan), so "Fix a day" opens Calendar rather than a blank form.
const ROUTES = {
	leave: { name: "LeaveApplicationFormView" },
	overtime: { name: "OTRequestFormView" },
	expense: { name: "ExpenseClaimFormView" },
	shift: { name: "ShiftRequestFormView" },
	fix: { name: "AttendanceDashboard" },
}
const requestTypes = [
	{ key: "leave", label: __("Time off") },
	{ key: "overtime", label: __("Claim overtime") },
	{ key: "expense", label: __("Claim an expense") },
	{ key: "shift", label: __("Change a shift") },
	{ key: "fix", label: __("Fix a day") },
]

const typeSheetOpen = ref(false)
function startRequest(key) {
	typeSheetOpen.value = false
	console.info("[Requests] new request", key)
	if (ROUTES[key]) router.push(ROUTES[key])
}

async function refreshRequests(event) {
	console.info("[Requests] pull-to-refresh")
	await reloadRequestLists("pull")
	event.target?.complete?.()
}
</script>
