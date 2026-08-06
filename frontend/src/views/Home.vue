<template>
	<BaseLayout>
		<template #body>
			<div
				class="flex flex-col gap-8 px-4 pt-6 pb-8 lg:grid lg:grid-cols-2 lg:gap-0 lg:p-7"
			>
				<div class="flex flex-col gap-8 lg:pr-8">
					<CheckInPanel />
					<QuickLinks :items="quickLinks" :title="__('Quick Links')" />
				</div>
				<div class="lg:border-l lg:border-divider lg:pl-8">
					<RequestPanel />
				</div>
			</div>
			<PushNotificationPrompt />
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject, markRaw } from "vue"

import { userResource } from "@/data/user"

import CheckInPanel from "@/components/CheckInPanel.vue"
import QuickLinks from "@/components/QuickLinks.vue"
import BaseLayout from "@/components/BaseLayout.vue"
import RequestPanel from "@/components/RequestPanel.vue"
import PushNotificationPrompt from "@/components/PushNotificationPrompt.vue"
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import ShiftIcon from "@/components/icons/ShiftIcon.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"
import EmployeeAdvanceIcon from "@/components/icons/EmployeeAdvanceIcon.vue"
import KPIIcon from "@/components/icons/KPIIcon.vue"
import SupportIcon from "@/components/icons/SupportIcon.vue"

const __ = inject("$translate")

const HR_BOARD_ROLES = ["HR User", "HR Manager", "System Manager"]
const isHR = computed(() =>
	(userResource.data?.roles || []).some((role) => HR_BOARD_ROLES.includes(role))
)

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
		icon: markRaw(EmployeeAdvanceIcon),
		title: __("Request an Advance"),
		route: "EmployeeAdvanceFormView",
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
	{
		icon: markRaw(SupportIcon),
		title: __("My Issues"),
		route: "EmployeeIssueListView",
	},
]

const quickLinks = computed(() => [
	...baseQuickLinks,
	...(isHR.value
		? [{ icon: markRaw(SupportIcon), title: __("HR Issue Board"), route: "HRIssueBoard" }]
		: []),
])
</script>
