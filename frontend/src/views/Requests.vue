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
				class="flex flex-col gap-5 px-4 pt-6 pb-8 w-full max-w-content-column-lg mx-auto lg:py-7"
			>
				<!-- Owner-approved one-screen layout (23 Sep 2026): the action
				     first, then the numbers as one line, then what needs you, then
				     your last five. ONE button, one type sheet (audit P1-B). -->
				<GButton :label="__('New request')" @click="typeSheetOpen = true" />
				<!-- §5: the numbers sit where the decision is made. The strip
				     renders nothing when there is nothing to say. -->
				<RequestBalances />
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
import { TILE } from "@/utils/iconTile"
import { inject, ref } from "vue"
import { CalendarCheck, CalendarClock, Clock, Palmtree, Receipt } from "lucide-vue-next"
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
//: on Help). "Fix a day" opens the fix form, which asks for the date, so the
//: person stays in Requests (it used to push Calendar into this tab).
const ROUTES = {
	leave: { name: "LeaveApplicationFormView" },
	overtime: { name: "OTRequestFormView" },
	expense: { name: "ExpenseClaimFormView" },
	shift: { name: "ShiftRequestFormView" },
	fix: { name: "AttendanceRequestFormView" },
}
//: Icon per kind = the one Notifications uses; the hint says what each is FOR
//: in the employee's words (owner, 24 Sep: "bad guidance design").
const requestTypes = [
	{
		key: "leave",
		tint: TILE.leave,
		label: __("Time off"),
		hint: __("Leave, sick days or a holiday"),
		icon: Palmtree,
	},
	{
		key: "overtime",
		tint: TILE.overtime,
		label: __("Claim overtime"),
		hint: __("Get paid for extra hours you worked"),
		icon: Clock,
	},
	{
		key: "expense",
		tint: TILE.expense,
		label: __("Claim an expense"),
		hint: __("Get back money you spent for work"),
		icon: Receipt,
	},
	{
		key: "shift",
		tint: TILE.shift,
		label: __("Change a shift"),
		hint: __("Work a different shift on some days"),
		icon: CalendarClock,
	},
	{
		key: "fix",
		tint: TILE.fix,
		label: __("Fix a day"),
		hint: __("A missing check-in, or a day on duty"),
		icon: CalendarCheck,
	},
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
