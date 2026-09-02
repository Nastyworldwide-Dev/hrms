<template>
	<div class="flex flex-col w-full gap-[13px]" v-if="calendarEvents.data">
		<GCalendar
			:title="`${firstOfMonth.format('MMMM')} ${firstOfMonth.format('YYYY')}`"
			:days="days"
			:leading-blanks="firstOfMonth.get('d')"
			:weekdays="DAYS"
			:legend="LEGEND"
		>
			<template #action>
				<!-- gap-3, not gap-2: each stepper expands its 44px target 6px past its
				     32px visual, so at 8px apart the two expanded areas overlapped and
				     one stole the other half. 12px is the first gap that fits both. -->
				<span class="flex gap-3">
					<button
						type="button"
						class="g-cal__nav g-focusable"
						:aria-label="__('Previous month')"
						@click="firstOfMonth = firstOfMonth.subtract(1, 'M')"
					>
						<svg class="g-icon" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
							<polyline points="10 3 5 8 10 13" />
						</svg>
					</button>
					<button
						type="button"
						class="g-cal__nav g-focusable"
						:aria-label="__('Next month')"
						@click="firstOfMonth = firstOfMonth.add(1, 'M')"
					>
						<svg class="g-icon" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
							<polyline points="6 3 11 8 6 13" />
						</svg>
					</button>
				</span>
			</template>
		</GCalendar>

		<!-- The month summary. §12's Attendance anatomy says a 3-up stat panel;
		     this screen summarises FOUR statuses, so GStatPanel takes columns=4
		     (v1.5: the app governs scope). -->
		<GStatPanel :columns="4">
			<GStatTile
				v-for="status in summaryStatuses"
				:key="status"
				:value="summary[status] || 0"
				:label="__(status)"
			/>
		</GStatPanel>
	</div>

	<!-- Without this the component rendered NOTHING when its request failed:
	     no calendar, no message, nothing to search for. Four features were
	     reported "missing" that were in fact erroring. -->
	<GBanner v-else-if="calendarEvents.error" variant="error">
		{{ __("Could not load the attendance calendar. Refresh to try again.") }}
	</GBanner>

	<!-- loading: the missing fourth state — the calendar auto-fetches, and
	     without this the component painted nothing until the first response. -->
	<GSkeleton v-else height="320px" />
</template>

<script setup>
import GBanner from "@/components/glass/GBanner.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import GStatTile from "@/components/glass/GStatTile.vue"
import GStatPanel from "@/components/glass/GStatPanel.vue"
import GCalendar from "@/components/glass/GCalendar.vue"
import { computed, inject, ref, watch } from "vue"
import { createResource } from "frappe-ui"

const dayjs = inject("$dayjs")
const __ = inject("$translate")
const firstOfMonth = ref(dayjs().date(1).startOf("D"))

// The API's attendance statuses → GCalendar's states. Work From Home folds
// into Present exactly as the summary rollup does, so the calendar and the
// counts below it cannot disagree.
const STATE = {
	Present: "present",
	"Work From Home": "present",
	"Half Day": "half",
	Absent: "absent",
	"On Leave": "leave",
	Holiday: "rest",
}

const LEGEND = [
	{ state: "present", label: __("Present") },
	{ state: "half", label: __("Half Day") },
	{ state: "absent", label: __("Absent") },
	{ state: "leave", label: __("On Leave") },
	{ state: "rest", label: __("Holiday") },
]

const days = computed(() =>
	Array.from({ length: firstOfMonth.value.endOf("M").get("D") }, (_, i) => {
		const day = i + 1
		return { day, state: STATE[getEventOnDate(day)] ?? "none" }
	})
)

// Day-cell and legend colour-coding for present/absent/leave/holiday now
// lives in GCalendar itself (state-driven, not inline style strings) — these
// two maps were the pre-GCalendar implementation and stopped being read by
// anything once the template below switched to `<GCalendar :days :legend>`.

// __("Present"), __("Half Day"), __("Absent"), __("On Leave"), __("Work From Home")
const summaryStatuses = ["Present", "Half Day", "Absent", "On Leave"]

const summary = computed(() => {
	const summary = {}

	for (const status of Object.values(calendarEvents.data)) {
		let updatedStatus = status === "Work From Home" ? "Present" : status
		if (updatedStatus in summary) {
			summary[updatedStatus] += 1
		} else {
			summary[updatedStatus] = 1
		}
	}

	return summary
})

watch(
	() => firstOfMonth.value,
	() => {
		calendarEvents.fetch()
	}
)

const getEventOnDate = (date) => {
	return calendarEvents.data[firstOfMonth.value.date(date).format("YYYY-MM-DD")]
}

const getDayAbbr = (s) => s.trim().slice(0, 3).toUpperCase() // Unicode-safe enough for labels

const DAYS = [
	getDayAbbr(__("Sunday")),
	getDayAbbr(__("Monday")),
	getDayAbbr(__("Tuesday")),
	getDayAbbr(__("Wednesday")),
	getDayAbbr(__("Thursday")),
	getDayAbbr(__("Friday")),
	getDayAbbr(__("Saturday")),
]

//resources
const calendarEvents = createResource({
	url: "hrms.api.get_attendance_calendar_events",
	auto: true,
	cache: "hrms:attendance_calendar_events",
	makeParams() {
		return {
			from_date: firstOfMonth.value.format("YYYY-MM-DD"),
			to_date: firstOfMonth.value.endOf("M").format("YYYY-MM-DD"),
		}
	},
})
</script>
