<template>
	<BaseLayout :pageTitle="__('Attendance')">
		<template #body>
			<div class="flex flex-col px-4 pt-6 pb-8 gap-8">
				<AttendanceCalendar />

				<router-link :to="{ name: 'AttendanceRequestFormView' }" v-slot="{ navigate }">
					<button type="button" class="m-btn-primary" @click="navigate">
						{{ __("Request Attendance") }}
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

				<div>
					<div class="flex items-baseline justify-between mb-2.5">
						<span class="m-kicker">{{ __("Recent Attendance Requests") }}</span>
						<router-link
							:to="{ name: 'AttendanceRequestListView' }"
							class="text-[11px] text-accent underline underline-offset-[3px]"
						>
							{{ __("View list") }}
						</router-link>
					</div>
					<hr class="m-rule" />
					<RequestList
						:component="markRaw(AttendanceRequestItem)"
						:items="myAttendanceRequests?.data?.slice(0, 5)"
					/>
				</div>

				<div>
					<div class="flex items-baseline justify-between mb-2.5">
						<span class="m-kicker">{{ __("Upcoming Shifts") }}</span>
						<router-link
							:to="{ name: 'ShiftAssignmentListView' }"
							class="text-[11px] text-accent underline underline-offset-[3px]"
						>
							{{ __("View list") }}
						</router-link>
					</div>
					<hr class="m-rule" />
					<RequestList
						:component="markRaw(ShiftAssignmentItem)"
						:items="upcomingShifts"
						:emptyStateMessage="__('You have no upcoming shifts')"
					/>
				</div>

				<router-link :to="{ name: 'ShiftRequestFormView' }" v-slot="{ navigate }">
					<button
						type="button"
						class="flex items-center w-full bg-transparent text-inkbase border border-divider px-4 py-3.5 font-bold text-sm text-left hover:bg-ink-200"
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

				<div>
					<div class="flex items-baseline justify-between mb-2.5">
						<span class="m-kicker">{{ __("Recent Shift Requests") }}</span>
						<router-link
							:to="{ name: 'ShiftRequestListView' }"
							class="text-[11px] text-accent underline underline-offset-[3px]"
						>
							{{ __("View list") }}
						</router-link>
					</div>
					<hr class="m-rule" />
					<RequestList
						:component="markRaw(ShiftRequestItem)"
						:items="myShiftRequests?.data?.slice(0, 5)"
					/>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject, markRaw } from "vue"
import { createResource } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import AttendanceRequestItem from "@/components/AttendanceRequestItem.vue"
import ShiftRequestItem from "@/components/ShiftRequestItem.vue"
import ShiftAssignmentItem from "@/components/ShiftAssignmentItem.vue"
import RequestList from "@/components/RequestList.vue"
import AttendanceCalendar from "@/components/AttendanceCalendar.vue"

import {
	getShiftDates,
	getTotalShiftDays,
	getShiftTiming,
	myAttendanceRequests,
	myShiftRequests,
} from "@/data/attendance"

const employee = inject("$employee")
const dayjs = inject("$dayjs")

const shifts = createResource({
	url: "hrms.api.get_shifts",
	auto: true,
	cache: "hrms:shifts",
	makeParams() {
		return {
			employee: employee.data?.name,
		}
	},
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
