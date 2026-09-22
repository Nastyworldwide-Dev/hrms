<template>
	<BaseLayout>
		<template #body>
			<!-- §20.3: ONE content column, 720px, left-aligned against the side nav.
			     Until the 7.3 ruling this split into lg:grid-cols-2 — measured 550px
			     and 549px, neither of them 720 — with the request panel behind a
			     border-l. Nothing in §20 authorised a screen splitting in two at
			     desktop, and the divergence was invisible below lg:, which is how
			     three build batches passed over it. Same correction on Leave and
			     Attendance. -->
			<!-- Pull to refresh: the socket is not a delivery guarantee on a phone,
			     so the employee always has a hand-driven way to see the decided
			     status without a full reload (A-C1). -->
			<!-- gap-5, not gap-8. The fold is a BUDGET, not a length:
			     USABLE = 100dvh - header - tab bar (64 + 9 + safe-area) -
			     padding, which is ~440px at 360x640 and ~640px at 390x844.
			     Four panels at gap-8 spent 96px of that on air alone, on a
			     screen measured at 1382px of content for ten tap targets.
			     Sized against the SMALLEST budget, every larger phone gains
			     list rows instead of needing its own layout. Invariant F1 and
			     the arithmetic: src/views/__tests__/home-fold-budget.test.js. -->
			<GPullRefresh @refresh="refreshRequests" />
			<div
				class="flex flex-col gap-5 px-4 pt-6 pb-8 w-full max-w-content-column-lg mx-auto lg:p-7"
			>
				<PendingApprovalsBanner />
				<CheckInPanel />
				<QuickLinks :items="quickLinks" :title="__('Quick Links')" />
				<RequestPanel />
			</div>
			<PushNotificationPrompt />
		</template>
	</BaseLayout>
</template>

<script setup>
import {
	CalendarClock,
	CalendarDays,
	ChartLine,
	LifeBuoy,
	CircleDollarSign,
	UserCheck,
} from "lucide-vue-next"
import { computed, inject, markRaw } from "vue"

import { reloadRequestLists } from "@/data/requestLists"
import { userResource } from "@/data/user"
import { HR_TAB, HUB_ROUTE_NAME } from "@/utils/helpdeskHub"
import { hasHRRole } from "@/utils/issueBoard"

import CheckInPanel from "@/components/CheckInPanel.vue"
import PendingApprovalsBanner from "@/components/PendingApprovalsBanner.vue"
import QuickLinks from "@/components/QuickLinks.vue"
import BaseLayout from "@/components/BaseLayout.vue"
import RequestPanel from "@/components/RequestPanel.vue"
import GPullRefresh from "@/components/glass/GPullRefresh.vue"
import PushNotificationPrompt from "@/components/PushNotificationPrompt.vue"

const __ = inject("$translate")

const isHR = computed(() => hasHRRole(userResource.data))

async function refreshRequests(event) {
	console.info("[Home] pull-to-refresh")
	await reloadRequestLists("pull")
	event.target?.complete?.()
}

const baseQuickLinks = [
	{
		icon: markRaw(UserCheck),
		title: __("Request Attendance"),
		route: "AttendanceRequestFormView",
	},
	{
		icon: markRaw(CalendarClock),
		title: __("Request a Shift"),
		route: "ShiftRequestFormView",
	},
	{
		icon: markRaw(CalendarDays),
		title: __("Request Leave"),
		route: "LeaveApplicationFormView",
	},
	{
		icon: markRaw(CircleDollarSign),
		title: __("Claim an Expense"),
		route: "ExpenseClaimFormView",
	},
	{
		icon: markRaw(ChartLine),
		title: __("My KPI"),
		route: "KPIDashboard",
	},
	{
		icon: markRaw(LifeBuoy),
		title: __("New HR Issue"),
		route: "EmployeeIssueFormView",
	},
]

// same destination for both — the HR Issues pill of the Helpdesk page renders
// the board for HR roles and the personal list for everyone else; only the
// label differs
const quickLinks = computed(() => [
	...baseQuickLinks,
	{
		icon: markRaw(LifeBuoy),
		title: isHR.value ? __("Issue Board") : __("HR Issues"),
		route: HUB_ROUTE_NAME,
		query: { tab: HR_TAB },
	},
])
</script>
