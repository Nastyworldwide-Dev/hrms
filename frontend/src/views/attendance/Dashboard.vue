<template>
	<BaseLayout :pageTitle="__('Attendance')">
		<template #body>
			<!-- §20.3: one 720px column (7.3 ruling). Was
			     lg:grid-cols-[1.1fr_1fr], which left ~320px of dead space in the
			     left column while the right overflowed the fold. -->
			<div
				class="flex flex-col px-4 pt-6 pb-8 gap-8 w-full max-w-content-column-lg mx-auto lg:p-7"
			>
				<div class="contents">
					<div class="order-1"><AttendanceCalendar /></div>
					<ResourceError :resource="shifts" what="your shifts" />
				</div>

				<div class="contents">
					<!-- PEERS, NO PRIMARY (§18 ranking rule, v1.11): equal-weight menu rows
					     in one panel (§15.2). Overtime and Replacement Leave used to be two
					     separate rows, but both are the SAME claim — you file the overtime
					     you worked, and whether it pays out or banks as replacement leave is
					     the employee's entitlement (HR-set), shown read-only on the form. One
					     row, "Claim Overtime or Leave". Managing/converting the replacement-
					     leave bank lives on the Leaves screen, where leave belongs. -->
					<div class="order-2">
						<GListPanel>
							<GListRow
								:label="__('Request Attendance')"
								@click="router.push({ name: 'AttendanceRequestFormView' })"
							/>
							<GListRow
								:label="__('Claim Overtime or Leave')"
								@click="router.push({ name: 'OTRequestFormView' })"
							/>
							<GListRow
								:label="__('Request a Shift')"
								@click="router.push({ name: 'ShiftRequestFormView' })"
							/>
						</GListPanel>
					</div>

					<div class="order-3">
						<div class="flex items-baseline justify-between mb-2.5">
							<span class="g-eyebrow">{{ __("Recent Attendance Requests") }}</span>
							<router-link
								:to="{ name: 'AttendanceRequestListView' }"
								class="g-seclink text-kra-label text-accent-ink underline underline-offset-link"
							>
								{{ __("View list") }}
							</router-link>
						</div>
						<hr class="h-px border-0 bg-hair" />
						<RequestList
							:component="markRaw(AttendanceRequestItem)"
							:items="myAttendanceRequests?.data?.slice(0, 5)"
							:resource="myAttendanceRequests"
							:what="__('your attendance requests')"
						/>
					</div>

					<div class="order-4">
						<div class="flex items-baseline justify-between mb-2.5">
							<span class="g-eyebrow">{{ __("Upcoming Shifts") }}</span>
							<router-link
								:to="{ name: 'ShiftAssignmentListView' }"
								class="g-seclink text-kra-label text-accent-ink underline underline-offset-link"
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

					<div class="order-5">
						<div class="flex items-baseline justify-between mb-2.5">
							<span class="g-eyebrow">{{ __("Recent Shift Requests") }}</span>
							<router-link
								:to="{ name: 'ShiftRequestListView' }"
								class="g-seclink text-kra-label text-accent-ink underline underline-offset-link"
							>
								{{ __("View list") }}
							</router-link>
						</div>
						<hr class="h-px border-0 bg-hair" />
						<RequestList
							:component="markRaw(ShiftRequestItem)"
							:items="myShiftRequests?.data?.slice(0, 5)"
							:resource="myShiftRequests"
							:what="__('your shift requests')"
						/>
					</div>

					<!-- OT Request was the only request type you could file and never
				     browse: OTRequestListView existed, was routed, and had no inbound
				     link anywhere in the app. -->
					<div class="order-6">
						<div class="flex items-baseline justify-between mb-2.5">
							<span class="g-eyebrow">{{ __("Recent OT Requests") }}</span>
							<router-link
								:to="{ name: 'OTRequestListView' }"
								class="g-seclink text-kra-label text-accent-ink underline underline-offset-link"
							>
								{{ __("View list") }}
							</router-link>
						</div>
						<hr class="h-px border-0 bg-hair" />
						<RequestList
							:component="markRaw(OTRequestItem)"
							:items="myOTRequests?.data?.slice(0, 5)"
							:resource="myOTRequests"
							:what="__('your OT requests')"
							:emptyStateMessage="__('You have no OT requests')"
						/>
					</div>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { useRouter } from "vue-router"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
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

const router = useRouter()
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
