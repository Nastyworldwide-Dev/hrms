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
				<QuickLinks :items="quickLinks" :title="__('Start a request')" />
				<RequestPanel />
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject, markRaw } from "vue"
import {
	CalendarClock,
	CalendarDays,
	CircleDollarSign,
	LifeBuoy,
	Receipt,
	UserCheck,
} from "lucide-vue-next"

import BaseLayout from "@/components/BaseLayout.vue"
import QuickLinks from "@/components/QuickLinks.vue"
import RequestBalances from "@/components/RequestBalances.vue"
import RequestPanel from "@/components/RequestPanel.vue"
import GPullRefresh from "@/components/glass/GPullRefresh.vue"

import { userResource } from "@/data/user"
import { reloadRequestLists } from "@/data/requestLists"
import { hasHRRole } from "@/utils/issueBoard"
import { HUB_ROUTE_NAME, HR_TAB } from "@/utils/helpdeskHub"

const __ = inject("$translate")

// The same destinations Home offers, because they are the same requests. Kept
// as this screen's own list rather than imported from Home: Home's list is
// Home's editorial choice (it shows what is used most often), and this one is
// meant to be complete. They agree today and are allowed to diverge.
const baseLinks = [
	{
		icon: markRaw(UserCheck),
		title: __("Fix a day"),
		route: "AttendanceRequestFormView",
	},
	{ icon: markRaw(CalendarClock), title: __("Change a shift"), route: "ShiftRequestFormView" },
	{ icon: markRaw(CalendarDays), title: __("Time off"), route: "LeaveApplicationFormView" },
	{
		icon: markRaw(CircleDollarSign),
		title: __("Claim an expense"),
		route: "ExpenseClaimFormView",
	},
	{ icon: markRaw(Receipt), title: __("Claim overtime"), route: "OTRequestFormView" },
]

const isHR = computed(() => hasHRRole(userResource.data))

const quickLinks = computed(() => [
	...baseLinks,
	{
		icon: markRaw(LifeBuoy),
		title: isHR.value ? __("Issue board") : __("HR Issues"),
		route: HUB_ROUTE_NAME,
		query: { tab: HR_TAB },
	},
])

async function refreshRequests(event) {
	console.info("[Requests] pull-to-refresh")
	await reloadRequestLists("pull")
	event.target?.complete?.()
}
</script>
