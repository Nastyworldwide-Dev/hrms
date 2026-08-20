<template>
	<BaseLayout :pageTitle="__('Attendance')">
		<template #body>
			<div
				class="flex flex-col px-4 pt-6 pb-8 gap-8 lg:grid lg:grid-cols-[1.1fr_1fr] lg:gap-x-0 lg:p-7 lg:items-start"
			>
				<div class="contents lg:flex lg:flex-col lg:gap-8 lg:pr-8">
					<div class="order-1"><AttendanceCalendar /></div>
					<ResourceError :resource="shifts" what="your shifts" />
				</div>

				<div
					class="contents lg:grid lg:grid-cols-2 lg:gap-x-3 lg:gap-y-8 lg:content-start lg:items-stretch lg:border-l lg:border-divider lg:pl-8"
				>
					<router-link
						:to="{ name: 'AttendanceRequestFormView' }"
						v-slot="{ navigate }"
						class="order-2 lg:order-1"
					>
						<GButton :label="__('Request Attendance')" class="h-full" @click="navigate">
							<template #trailing>
								<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
									<line x1="5" y1="12" x2="19" y2="12"></line>
									<polyline points="12 5 19 12 12 19"></polyline>
								</svg>
							</template>
						</GButton>
					</router-link>

					<router-link
						:to="{ name: 'OTRequestFormView' }"
						v-slot="{ navigate }"
						class="order-6 lg:order-3"
					>
						<button
							type="button"
							class="flex items-center w-full h-full bg-transparent text-inkbase border border-divider px-4 py-3.5 font-bold text-sm text-left hover:bg-ink-200"
							@click="navigate"
						>
							{{ __("Request Overtime") }}
							<svg
								width="17"
								height="17"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
								class="ml-auto"
							>
								<line x1="5" y1="12" x2="19" y2="12" />
								<polyline points="12 5 19 12 12 19" />
							</svg>
						</button>
					</router-link>

					<router-link
						:to="{ name: 'ReplacementLeaveView' }"
						v-slot="{ navigate }"
						class="order-7 lg:order-4"
					>
						<button
							type="button"
							class="flex items-center w-full h-full bg-transparent text-inkbase border border-divider px-4 py-3.5 font-bold text-sm text-left hover:bg-ink-200"
							@click="navigate"
						>
							{{ __("Replacement Leave") }}
							<svg
								width="17"
								height="17"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
								class="ml-auto"
							>
								<line x1="5" y1="12" x2="19" y2="12" />
								<polyline points="12 5 19 12 12 19" />
							</svg>
						</button>
					</router-link>

					<router-link
						:to="{ name: 'ShiftRequestFormView' }"
						v-slot="{ navigate }"
						class="order-5 lg:order-2"
					>
						<button
							type="button"
							class="flex items-center w-full h-full bg-transparent text-inkbase border border-divider px-4 py-3.5 font-bold text-sm text-left hover:bg-ink-200"
							@click="navigate"
						>
							{{ __("Request a Shift") }}
							<svg
								width="17"
								height="17"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
								class="ml-auto"
							>
								<line x1="5" y1="12" x2="19" y2="12" />
								<polyline points="12 5 19 12 12 19" />
							</svg>
						</button>
					</router-link>

					<div class="order-3 lg:order-3 lg:col-span-2">
						<div class="flex items-baseline justify-between mb-2.5">
							<span class="text-eyebrow uppercase text-accent-ink">{{ __("Recent Attendance Requests") }}</span>
							<router-link
								:to="{ name: 'AttendanceRequestListView' }"
								class="text-kra-label text-accent underline underline-offset-link"
							>
								{{ __("View list") }}
							</router-link>
						</div>
						<hr class="h-px border-0 bg-hair" />
						<RequestList
							:component="markRaw(AttendanceRequestItem)"
							:items="myAttendanceRequests?.data?.slice(0, 5)"
						/>
					</div>

					<div class="order-4 lg:order-4 lg:col-span-2">
						<div class="flex items-baseline justify-between mb-2.5">
							<span class="text-eyebrow uppercase text-accent-ink">{{ __("Upcoming Shifts") }}</span>
							<router-link
								:to="{ name: 'ShiftAssignmentListView' }"
								class="text-kra-label text-accent underline underline-offset-link"
							>
								{{ __("View list") }}
							</router-link>
						</div>
						<hr class="h-px border-0 bg-hair" />
						<RequestList
							:component="markRaw(ShiftAssignmentItem)"
							:items="upcomingShifts"
							:emptyStateMessage="__('You have no upcoming shifts')"
						/>
					</div>

					<div class="order-6 lg:order-5 lg:col-span-2">
						<div class="flex items-baseline justify-between mb-2.5">
							<span class="text-eyebrow uppercase text-accent-ink">{{ __("Recent Shift Requests") }}</span>
							<router-link
								:to="{ name: 'ShiftRequestListView' }"
								class="text-kra-label text-accent underline underline-offset-link"
							>
								{{ __("View list") }}
							</router-link>
						</div>
						<hr class="h-px border-0 bg-hair" />
						<RequestList
							:component="markRaw(ShiftRequestItem)"
							:items="myShiftRequests?.data?.slice(0, 5)"
						/>
					</div>

					<!-- OT Request was the only request type you could file and never
				     browse: OTRequestListView existed, was routed, and had no inbound
				     link anywhere in the app. -->
					<div class="order-7 lg:order-6 lg:col-span-2">
						<div class="flex items-baseline justify-between mb-2.5">
							<span class="text-eyebrow uppercase text-accent-ink">{{ __("Recent OT Requests") }}</span>
							<router-link
								:to="{ name: 'OTRequestListView' }"
								class="text-kra-label text-accent underline underline-offset-link"
							>
								{{ __("View list") }}
							</router-link>
						</div>
						<hr class="h-px border-0 bg-hair" />
						<RequestList
							:component="markRaw(OTRequestItem)"
							:items="myOTRequests?.data?.slice(0, 5)"
							:emptyStateMessage="__('You have no OT requests')"
						/>
					</div>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import GButton from "@/components/glass/GButton.vue"
import { computed, inject, markRaw } from "vue"
import { createResource } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import AttendanceRequestItem from "@/components/AttendanceRequestItem.vue"
import ShiftRequestItem from "@/components/ShiftRequestItem.vue"
import OTRequestItem from "@/components/OTRequestItem.vue"
import ShiftAssignmentItem from "@/components/ShiftAssignmentItem.vue"
import RequestList from "@/components/RequestList.vue"
import ResourceError from "@/components/ResourceError.vue"
import AttendanceCalendar from "@/components/AttendanceCalendar.vue"

import {
	getShiftDates,
	getTotalShiftDays,
	getShiftTiming,
	myAttendanceRequests,
	myShiftRequests,
} from "@/data/attendance"
import { myOTRequests } from "@/data/overtime"

const dayjs = inject("$dayjs")

const shifts = createResource({
	url: "hrms.api.get_shifts",
	auto: true,
	cache: "hrms:shifts",
	transform: (data) => {
		return data.map((assignment) => {
			assignment.doctype = "Shift Assignment"
			assignment.is_upcoming = !assignment.end_date || dayjs(assignment.end_date).isAfter(dayjs())
			assignment.shift_dates = getShiftDates(assignment)
			assignment.total_shift_days = getTotalShiftDays(assignment)
			assignment.shift_timing = getShiftTiming(assignment)
			return assignment
		})
	},
})

const upcomingShifts = computed(() => {
	const filteredShifts = shifts.data?.filter((shift) => shift.is_upcoming)

	// show only 5 upcoming shifts
	return filteredShifts?.slice(0, 5)
})
</script>
