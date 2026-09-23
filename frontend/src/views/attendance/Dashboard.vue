<template>
	<BaseLayout :pageTitle="__('Calendar')">
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
											: __("{0} h waiting", [formatHours(claimableOt.data.claimable_hours)])
									}}
								</span>
								<span class="text-sm text-ink-600">
									{{ __("{0} · tap to claim", [claimOutcome]) }}
								</span>
							</div>
							<span class="text-accent-ink text-xl" aria-hidden="true">→</span>
						</button>
					</div>
					<div class="order-1"><AttendanceCalendar ref="calendar" /></div>
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
								:label="__('Fix a day')"
								@click="router.push({ name: 'AttendanceRequestFormView' })"
							/>
							<GListRow
								:label="__('Claim overtime')"
								@click="router.push({ name: 'OTRequestFormView' })"
							/>
							<GListRow
								:label="__('Change a shift')"
								@click="router.push({ name: 'ShiftRequestFormView' })"
							/>
						</GListPanel>
					</div>

					<!-- THE FOUR LISTS ARE GONE (revamp §4).
					     This screen carried "Recent attendance requests", "Upcoming
					     shifts", "Recent shift requests" and "Recent OT requests" —
					     four stacked sections, three of them usually empty, below a
					     calendar that already knows every one of those facts. The
					     prototype's own flow map said to delete them ("one request list
					     with chips replaces four empty sections") and 2.0 shipped with
					     them still there; so did the first revamp pass.

					     Nothing was lost. A day's punches, shift and status are in the
					     DAY SHEET, one tap from any tile. Every request, of every type,
					     with its chip, is the Requests tab — which is a destination in
					     the bar now and was not when these lists were added.

					     What stays is this one row: the way to the full punch history,
					     which is the only thing here the calendar does NOT show. -->
					<div class="order-3">
						<GListPanel>
							<GListRow
								:label="__('View all your check-ins')"
								:sublabel="__('Every tap, newest first')"
								@click="router.push({ name: 'EmployeeCheckinListView' })"
							/>
							<GListRow
								:label="__('Your shifts')"
								:sublabel="__('Assigned and upcoming')"
								@click="router.push({ name: 'ShiftAssignmentListView' })"
							/>
						</GListPanel>
					</div>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { personalCacheKey } from "@/utils/personalCache"
import { createResource } from "frappe-ui"
import { computed, inject, ref } from "vue"
import { useRouter } from "vue-router"
import { onIonViewWillEnter } from "@ionic/vue"
import AttendanceCalendar from "@/components/AttendanceCalendar.vue"

import BaseLayout from "@/components/BaseLayout.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import ResourceError from "@/components/ResourceError.vue"

// The five request-row components and their three list resources went with the
// four sections above (revamp §4). Every one of those lists lives on the
// Requests tab now, which did not exist when they were added here.
import { settings } from "@/data/settings"
import { formatHours } from "@/utils/formatters"

const router = useRouter()

// The calendar stays mounted while the tab is in the Ionic stack, so a day
// the hourly job processed while the employee was on another tab never
// showed until a full reload. Re-entering the view refreshes the month.
const calendar = ref(null)
onIonViewWillEnter(() => calendar.value?.refresh?.())
// This file had never needed `__` in the SCRIPT — every call was in the
// template, where Vue resolves it from globalProperties. A computed that
// builds a word needs the real function.
const __ = inject("$translate")

// Overtime the employee has worked but not yet filed — drives the "to claim" card
// at the top of the screen so it is discoverable, not accidental. Session-scoped.
const claimableOt = createResource({
	url: "hrms.api.get_claimable_ot_summary",
	auto: true,
})

//: The two wire values of `compensation` — the doctype's Select options,
//: which cannot change without a migration. Mapped explicitly rather than
//: passed through `__()`: the translation files carry UI strings, not doctype
//: values, so translating the raw value is precisely how "Overtime Pay"
//: reaches an employee's screen. Same defect, same fix as the OT row
//: (2.0 slice 2.2) and the shift chip (1.2).
const CLAIM_OUTCOME = {
	"Overtime Pay": () => __("Overtime pay"),
	"Replacement Leave": () => __("A day off in return"),
}

const claimOutcome = computed(() => {
	const chosen = CLAIM_OUTCOME[claimableOt.data?.compensation]
	return chosen ? chosen() : __("Overtime")
})

const isRLClaim = computed(() => claimableOt.data?.compensation === "Replacement Leave")

// Replacement Leave is earned in whole 4h blocks PER DAY (mirrors backend
// replacement_leave_days); sum the block-days across the claimable days. Days under
// 4h earn nothing, so they add 0.
const claimLeaveDays = computed(() => {
	const half = (settings.data?.replacement_leave_hours_per_day ?? 8) / 2
	if (half <= 0) return 0
	return (claimableOt.data?.days || []).reduce(
		(sum, d) => sum + Math.floor((d.hours || 0) / half) * 0.5,
		0
	)
})

// Show the card only when there is really something to claim: hours for Overtime
// Pay, at least one full 4h block of leave for Replacement Leave.
const hasClaim = computed(() =>
	isRLClaim.value ? claimLeaveDays.value > 0 : (claimableOt.data?.claimable_hours || 0) > 0
)

// Still fetched, and only so the screen can SAY when shifts cannot be read —
// a silent failure here is an employee who thinks they have no shift. The
// transform that decorated each row for the Upcoming Shifts list went with
// that list; the shifts screen itself does its own decorating.
const shifts = createResource({
	url: "hrms.api.get_shifts",
	auto: true,
	cache: personalCacheKey("hrms:shifts"),
})
</script>
