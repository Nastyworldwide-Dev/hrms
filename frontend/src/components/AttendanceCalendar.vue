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
		{{ __("Could not load the attendance calendar.") }}
		<button type="button" class="ml-2 underline g-focusable" @click="refresh">
			{{ __("Try again") }}
		</button>
	</GBanner>

	<!-- loading: the missing fourth state — the calendar auto-fetches, and
	     without this the component painted nothing until the first response. -->
	<GSkeleton v-else height="320px" />
</template>

<script setup>
import { personalCacheKey } from "@/utils/personalCache"
import GBanner from "@/components/glass/GBanner.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import GStatTile from "@/components/glass/GStatTile.vue"
import GStatPanel from "@/components/glass/GStatPanel.vue"
import GCalendar from "@/components/glass/GCalendar.vue"
import { computed, inject, ref } from "vue"
import { createResource } from "frappe-ui"
import { useListUpdate } from "@/composables/realtime"

const dayjs = inject("$dayjs")
const __ = inject("$translate")
const socket = inject("$socket", null)
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

	for (const status of Object.values(calendarEvents.value.data || {})) {
		let updatedStatus = status === "Work From Home" ? "Present" : status
		if (updatedStatus in summary) {
			summary[updatedStatus] += 1
		} else {
			summary[updatedStatus] = 1
		}
	}

	return summary
})

const getEventOnDate = (date) => {
	return (calendarEvents.value.data || {})[firstOfMonth.value.date(date).format("YYYY-MM-DD")]
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

// One resource PER MONTH, owned by that month. The old single resource took
// whichever response finished last: step from September to October while
// September was still loading and September's rows were painted under
// October's title. Each month now answers only for itself, and a month that
// was already fetched shows at once when stepped back to.
const months = new Map()
function monthResource(firstDay) {
	const key = firstDay.format("YYYY-MM")
	if (!months.has(key)) {
		const resource = createResource({
			url: "hrms.api.get_attendance_calendar_events",
			params: {
				from_date: firstDay.format("YYYY-MM-DD"),
				to_date: firstDay.endOf("M").format("YYYY-MM-DD"),
			},
			cache: personalCacheKey(`hrms:attendance_calendar_events:${key}`),
		})
		months.set(key, resource)
		// The banner renders resource.error; the rejection itself is owned here
		// so a failed month never surfaces as an unhandled promise.
		resource.fetch().catch(() => console.warn("[AttendanceCalendar] month unavailable", key))
	}
	return months.get(key)
}
const calendarEvents = computed(() => monthResource(firstOfMonth.value))

// A processed day never reached a calendar that was already open: the hourly
// job's Attendance appeared only after a full reload. Reload the month on
// show whenever an Attendance row changes, and on demand (view re-entry, the
// error banner's Try again).
function refresh() {
	const key = firstOfMonth.value.format("YYYY-MM")
	console.info("[AttendanceCalendar] refreshing", key)
	calendarEvents.value
		.reload()
		.catch(() => console.warn("[AttendanceCalendar] refresh failed", key))
}
useListUpdate(socket, "Attendance", refresh)
defineExpose({ refresh })
</script>
