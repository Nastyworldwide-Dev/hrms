<template>
	<div class="flex flex-col w-full" v-if="calendarEvents.data">
		<!-- Month heading + navigation -->
		<div class="flex items-center justify-between mb-4">
			<h2 class="text-[22px] leading-none">
				{{ firstOfMonth.format("MMMM") }} {{ firstOfMonth.format("YYYY") }}
			</h2>
			<div class="flex gap-2">
				<button
					type="button"
					class="w-9 h-9 flex items-center justify-center border border-divider text-inkbase hover:bg-ink-200"
					@click="firstOfMonth = firstOfMonth.subtract(1, 'M')"
				>
					<svg
						width="15"
						height="15"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<polyline points="15 18 9 12 15 6" />
					</svg>
				</button>
				<button
					type="button"
					class="w-9 h-9 flex items-center justify-center border border-divider text-inkbase hover:bg-ink-200"
					@click="firstOfMonth = firstOfMonth.add(1, 'M')"
				>
					<svg
						width="15"
						height="15"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<polyline points="9 18 15 12 9 6" />
					</svg>
				</button>
			</div>
		</div>

		<!-- Calendar grid -->
		<div class="grid grid-cols-7 gap-y-2 border-t-2 border-divider pt-3">
			<div
				v-for="day in DAYS"
				class="text-center text-[9px] tracking-[0.1em] uppercase text-ink-500 font-bold"
			>
				{{ day }}
			</div>
			<div v-for="_ in firstOfMonth.get('d')" />
			<div v-for="index in firstOfMonth.endOf('M').get('D')" class="flex justify-center">
				<div
					class="aspect-square w-full max-w-[40px] flex items-center justify-center text-[13px]"
					:style="getEventOnDate(index) && dayStyle[getEventOnDate(index)]"
				>
					{{ index }}
				</div>
			</div>
		</div>

		<!-- Summary -->
		<div class="grid grid-cols-4 border-t-2 border-divider mt-4 pt-3">
			<div v-for="status in summaryStatuses" class="flex flex-col gap-0.5">
				<span class="m-statnum" style="font-size: 20px">
					{{ summary[status] || 0 }}
				</span>
				<span
					class="flex items-center gap-1.5 text-[9px] tracking-[0.08em] uppercase text-ink-600"
				>
					<span class="flex-none w-[9px] h-[9px]" :style="swatchStyle[status]" />
					{{ __(status) }}
				</span>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue"
import { createResource } from "frappe-ui"

const dayjs = inject("$dayjs")
const employee = inject("$employee")
const __ = inject("$translate")
const firstOfMonth = ref(dayjs().date(1).startOf("D"))

// Day-cell styles for the mono/accent scheme. Work From Home folds into the
// Present style (mirrors the summary rollup); Holiday maps to the muted
// neutral treatment since the design's swatch set is Present/Half/Absent/Leave.
const dayStyle = {
	Present: "background:var(--color-neutral-300)",
	"Work From Home": "background:var(--color-neutral-300)",
	"Half Day":
		"background:linear-gradient(135deg,var(--color-neutral-400) 50%,var(--color-neutral-200) 50%)",
	Absent: "background:var(--color-accent);color:var(--color-bg);font-weight:600",
	"On Leave": "border:2px solid var(--color-accent);color:var(--color-accent-700);font-weight:600",
	Holiday: "color:var(--color-neutral-400)",
}

// 9px legend swatches mirroring each day-cell style.
const swatchStyle = {
	Present: "background:var(--color-neutral-300)",
	"Half Day":
		"background:linear-gradient(135deg,var(--color-neutral-400) 50%,var(--color-neutral-200) 50%)",
	Absent: "background:var(--color-accent)",
	"On Leave": "border:1.5px solid var(--color-accent)",
}

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
			employee: employee.data.name,
			from_date: firstOfMonth.value.format("YYYY-MM-DD"),
			to_date: firstOfMonth.value.endOf("M").format("YYYY-MM-DD"),
		}
	},
})
</script>
