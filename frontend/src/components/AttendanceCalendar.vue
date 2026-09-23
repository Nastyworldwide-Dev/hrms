<template>
	<div class="flex flex-col w-full gap-3" v-if="calendarEvents.data">
		<GCalendar
			:title="`${firstOfMonth.format('MMMM')} ${firstOfMonth.format('YYYY')}`"
			:days="days"
			:leading-blanks="firstOfMonth.get('d')"
			:weekdays="DAYS"
			:legend="monthLegend"
			@select="openDay"
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

		<!-- The words. One tap from the grid, so the tiles never have to carry
		     a sentence (revamp §4). -->
		<DaySheet :open="sheetOpen" :date="sheetDate" @close="sheetOpen = false" />
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
import GCalendar from "@/components/glass/GCalendar.vue"
import DaySheet from "@/components/DaySheet.vue"

import { monthFlags } from "@/data/calendar"
import { legendFor } from "@/utils/calendarLegend"
import { computed, inject, ref, watch } from "vue"
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

//: The legend words of the approved Calendar plan (§3): the person's words,
//: not the attendance statuses. "Rest day" covers weekly offs and public
//: holidays alike; the day sheet names the holiday.
const LEGEND = [
	{ state: "present", label: __("Worked") },
	{ state: "half", label: __("Half day") },
	{ state: "leave", label: __("Leave") },
	{ state: "rest", label: __("Rest day") },
	{ state: "absent", label: __("Absent") },
]

const days = computed(() =>
	Array.from({ length: firstOfMonth.value.endOf("M").get("D") }, (_, i) => {
		const day = i + 1
		// state is WHAT KIND of day it was; flags are what ELSE was on it
		// (revamp §4). Two reads rather than one: the status comes from the
		// attendance calendar this screen has always used, and the dots from
		// the flags endpoint, so neither has to know about the other.
		const iso = firstOfMonth.value.date(day).format("YYYY-MM-DD")
		return {
			day,
			state: STATE[getEventOnDate(day)] ?? "none",
			flags: monthFlags.data?.flags?.[iso] || [],
			// Where am I? (approved Calendar plan, D6; Nielsen 1)
			today: iso === dayjs().format("YYYY-MM-DD"),
		}
	})
)

//: Only the states this month has (approved Calendar plan, C6).
const monthLegend = computed(() => legendFor(LEGEND, days.value))


// Day-cell and legend colour-coding for present/absent/leave/holiday now
// lives in GCalendar itself (state-driven, not inline style strings) — these
// two maps were the pre-GCalendar implementation and stopped being read by
// anything once the template below switched to `<GCalendar :days :legend>`.

// __("Present"), __("Half day"), __("Absent"), __("On leave"), __("Work from home")

//: The day sheet. Opened by tapping a tile, closed by the sheet itself — a
//: swipe and a backdrop tap dismiss it too, and a parent that only listens to
//: a button is left with `open` stuck true.
const sheetDate = ref("")
const sheetOpen = ref(false)

function openDay(day) {
	sheetDate.value = firstOfMonth.value.date(day).format("YYYY-MM-DD")
	sheetOpen.value = true
}

//: Flags follow the month being LOOKED AT, not the month it was mounted in.
//: Watched rather than fetched once, or stepping to October would draw
//: September's dots under October's dates — the same defect the per-month
//: attendance resources above were built to prevent.
watch(
	firstOfMonth,
	(month) => {
		monthFlags.fetch({
			from_date: month.format("YYYY-MM-DD"),
			to_date: month.endOf("M").format("YYYY-MM-DD"),
		})
	},
	{ immediate: true }
)

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
