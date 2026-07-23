<template>
	<ion-tab-bar
		slot="bottom"
		class="bg-ground border-t-2 border-divider standalone:pb-safe-bottom lg:hidden"
	>
		<ion-tab-button
			v-for="item in tabItems"
			:key="item.title"
			:tab="item.title"
			:href="item.route"
			:class="[
				'relative bg-ground pt-2 pb-3 space-y-1 transition active:scale-95',
				route.path === item.route ? 'text-inkbase' : 'text-ink-500',
			]"
		>
			<span
				class="absolute top-0 inset-x-0 h-[3px]"
				:class="route.path === item.route ? 'bg-accent' : 'bg-transparent'"
			></span>
			<component :is="item.icon" class="h-5 w-5" />
			<div class="text-[9px] uppercase font-extrabold tracking-[0.08em]">
				{{ item.title }}
			</div>
		</ion-tab-button>
	</ion-tab-bar>
</template>

<script setup>
import { useRoute } from "vue-router"

import { IonTabBar, IonTabButton, IonLabel } from "@ionic/vue"

import HomeIcon from "@/components/icons/HomeIcon.vue"
import LeaveIcon from "@/components/icons/LeaveIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"
import SalaryIcon from "@/components/icons/SalaryIcon.vue"
import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import KPIIcon from "@/components/icons/KPIIcon.vue"
import { inject } from "vue"

const __ = inject("$translate")

const route = useRoute()

const tabItems = [
	{
		icon: HomeIcon,
		title: __("Home"),
		route: "/home",
	},
	{
		icon: AttendanceIcon,
		title: __("Attendance"),
		route: "/dashboard/attendance",
	},
	{
		icon: LeaveIcon,
		title: __("Leaves"),
		route: "/dashboard/leaves",
	},
	{
		icon: ExpenseIcon,
		title: __("Expenses"),
		route: "/dashboard/expense-claims",
	},
	{
		icon: SalaryIcon,
		title: __("Salary"),
		route: "/dashboard/salary-slips",
	},
	{
		icon: KPIIcon,
		title: __("My KPI"),
		route: "/dashboard/kpi",
	},
]
</script>
