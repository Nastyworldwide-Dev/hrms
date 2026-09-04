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
					<!-- Overtime already worked, surfaced so it is not a secret you find by
					     opening the form and guessing a date. Tappable straight into the
					     claim; hidden when there is nothing to claim. -->
					<div v-if="hasClaim" class="order-0">
						<button
							class="w-full text-left border border-accent-ink rounded-panel p-4 flex items-center justify-between gap-3 cursor-pointer hover:bg-icon-bg"
							@click="router.push({ name: 'OTRequestFormView' })"
						>
							<div class="flex flex-col gap-1">
								<span class="g-eyebrow text-accent-ink">{{ __("Overtime to claim") }}</span>
								<span class="text-lg font-extrabold text-inkbase">
									{{
										isRLClaim
											? __("{0} day(s) off waiting", [claimLeaveDays])
											: __("{0} h waiting", [claimableOt.data.claimable_hours])
									}}
								</span>
								<span class="text-sm text-ink-600">
									{{ __("{0} · tap to claim", [__(claimableOt.data.compensation)]) }}
								</span>
							</div>
							<span class="text-accent-ink text-xl" aria-hidden="true">→</span>
						</button>
					</div>
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
import { createResource } from "frappe-ui";
import { computed, inject, markRaw } from "vue";
import { useRouter } from "vue-router";
import AttendanceCalendar from "@/components/AttendanceCalendar.vue";
import AttendanceRequestItem from "@/components/AttendanceRequestItem.vue";

import BaseLayout from "@/components/BaseLayout.vue";
import GListPanel from "@/components/glass/GListPanel.vue";
import GListRow from "@/components/glass/GListRow.vue";
import OTRequestItem from "@/components/OTRequestItem.vue";
import RequestList from "@/components/RequestList.vue";
import ResourceError from "@/components/ResourceError.vue";
import ShiftAssignmentItem from "@/components/ShiftAssignmentItem.vue";
import ShiftRequestItem from "@/components/ShiftRequestItem.vue";

import {
	getShiftDates,
	getShiftTiming,
	getTotalShiftDays,
	myAttendanceRequests,
	myShiftRequests,
} from "@/data/attendance";
import { myOTRequests } from "@/data/overtime";
import { settings } from "@/data/settings";

const router = useRouter();
const dayjs = inject("$dayjs");

// Overtime the employee has worked but not yet filed — drives the "to claim" card
// at the top of the screen so it is discoverable, not accidental. Session-scoped.
const claimableOt = createResource({
	url: "hrms.api.get_claimable_ot_summary",
	auto: true,
});

const isRLClaim = computed(
	() => claimableOt.data?.compensation === "Replacement Leave",
);

// Replacement Leave is earned in whole 4h blocks PER DAY (mirrors backend
// replacement_leave_days); sum the block-days across the claimable days. Days under
// 4h earn nothing, so they add 0.
const claimLeaveDays = computed(() => {
	const half = (settings.data?.replacement_leave_hours_per_day ?? 8) / 2;
	if (half <= 0) return 0;
	return (claimableOt.data?.days || []).reduce(
		(sum, d) => sum + Math.floor((d.hours || 0) / half) * 0.5,
		0,
	);
});

// Show the card only when there is really something to claim: hours for Overtime
// Pay, at least one full 4h block of leave for Replacement Leave.
const hasClaim = computed(() =>
	isRLClaim.value
		? claimLeaveDays.value > 0
		: (claimableOt.data?.claimable_hours || 0) > 0,
);

const shifts = createResource({
	url: "hrms.api.get_shifts",
	auto: true,
	cache: "hrms:shifts",
	transform: (data) => {
		return data.map((assignment) => {
			assignment.doctype = "Shift Assignment";
			assignment.is_upcoming =
				!assignment.end_date || dayjs(assignment.end_date).isAfter(dayjs());
			assignment.shift_dates = getShiftDates(assignment);
			assignment.total_shift_days = getTotalShiftDays(assignment);
			assignment.shift_timing = getShiftTiming(assignment);
			return assignment;
		});
	},
});

const upcomingShifts = computed(() => {
	const filteredShifts = shifts.data?.filter((shift) => shift.is_upcoming);

	// show only 5 upcoming shifts
	return filteredShifts?.slice(0, 5);
});
</script>
