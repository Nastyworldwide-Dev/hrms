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
			<div
				class="flex flex-col gap-8 px-4 pt-6 pb-8 w-full max-w-content-column-lg mx-auto lg:p-7"
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
import { computed, inject, markRaw } from "vue"

import { userResource } from "@/data/user"
import { hasHRRole } from "@/utils/issueBoard"

import CheckInPanel from "@/components/CheckInPanel.vue"
import PendingApprovalsBanner from "@/components/PendingApprovalsBanner.vue"
import QuickLinks from "@/components/QuickLinks.vue"
import BaseLayout from "@/components/BaseLayout.vue"
import RequestPanel from "@/components/RequestPanel.vue"
import PushNotificationPrompt from "@/components/PushNotificationPrompt.vue"
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import ShiftIcon from "@/components/icons/ShiftIcon.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"
import KPIIcon from "@/components/icons/KPIIcon.vue"
import SupportIcon from "@/components/icons/SupportIcon.vue"

const __ = inject("$translate")

const isHR = computed(() => hasHRRole(userResource.data))

const baseQuickLinks = [
	{
		icon: markRaw(AttendanceIcon),
		title: __("Request Attendance"),
		route: "AttendanceRequestFormView",
	},
	{
		icon: markRaw(ShiftIcon),
		title: __("Request a Shift"),
		route: "ShiftRequestFormView",
	},
	{
		icon: markRaw(LeaveIcon),
		title: __("Request Leave"),
		route: "LeaveApplicationFormView",
	},
	{
		icon: markRaw(ExpenseIcon),
		title: __("Claim an Expense"),
		route: "ExpenseClaimFormView",
	},
	{
		icon: markRaw(KPIIcon),
		title: __("My KPI"),
		route: "KPIDashboard",
	},
	{
		icon: markRaw(SupportIcon),
		title: __("Report an Issue"),
		route: "EmployeeIssueFormView",
	},
]

// same destination for both — the Issues tab renders the board for HR roles
// and the personal list for everyone else; only the label differs
const quickLinks = computed(() => [
	...baseQuickLinks,
	{
		icon: markRaw(SupportIcon),
		title: isHR.value ? __("Issue Board") : __("My Issues"),
		route: "EmployeeIssueListView",
	},
])
</script>
