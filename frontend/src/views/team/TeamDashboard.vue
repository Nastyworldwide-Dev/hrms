<template>
	<BaseLayout :pageTitle="__('Team')">
		<template #body>
			<div class="flex flex-col gap-5 w-full max-w-[720px] px-4 pt-[18px] pb-24 lg:p-7">
				<!-- HR-only team selector -->
				<div
					v-if="teamManagers.data?.length"
					class="flex flex-row items-center gap-2"
				>
					<span class="m-kicker flex-none">{{ __("Team of") }}</span>
					<select
						v-model="selectedManager"
						@change="fetchDay"
						class="flex-1 min-w-0 bg-surface border border-divider text-inkbase font-semibold text-[12px] p-2 appearance-none"
					>
						<option value="">{{ __("My team") }}</option>
						<option
							v-for="manager in teamManagers.data"
							:key="manager.name"
							:value="manager.name"
						>
							{{ manager.employee_name }}
						</option>
					</select>
				</div>

				<!-- day navigation -->
				<div class="flex flex-row items-center justify-between">
					<button
						class="flex items-center justify-center w-[34px] h-[34px] border border-divider bg-transparent text-inkbase"
						@click="changeDay(-1)"
						:aria-label="__('Previous day')"
					>
						<FeatherIcon name="chevron-left" class="h-4 w-4" />
					</button>
					<span
						class="font-sans font-extrabold text-[12px] tracking-[0.08em] uppercase text-inkbase"
					>
						{{ dayLabel }}
					</span>
					<button
						class="flex items-center justify-center w-[34px] h-[34px] border border-divider bg-transparent text-inkbase"
						@click="changeDay(1)"
						:aria-label="__('Next day')"
					>
						<FeatherIcon name="chevron-right" class="h-4 w-4" />
					</button>
				</div>

				<ResourceError :resource="teamStatus" what="your team's status" />
				<!-- summary tiles -->
				<div class="grid grid-cols-4 border-t-2 border-divider" v-if="teamStatus.data">
					<div
						v-for="(tile, index) in summaryTiles"
						:key="tile.label"
						class="flex flex-col gap-1 px-2.5 py-3"
						:class="index !== 0 ? 'border-l border-divider' : ''"
					>
						<span class="font-sans font-extrabold text-[22px] leading-none text-inkbase">
							{{ tile.count }}
						</span>
						<span class="text-[9px] tracking-[0.08em] uppercase text-ink-600 leading-tight">
							{{ tile.label }}
						</span>
					</div>
				</div>

				<!-- member rows -->
				<div
					class="flex flex-col border-t-2 border-divider"
					v-if="teamStatus.data?.members?.length"
				>
					<div
						v-for="member in teamStatus.data.members"
						:key="member.employee"
						class="flex flex-col bg-surface border-b border-divider p-3 cursor-pointer"
						@click="toggleRow(member.employee)"
					>
						<div class="flex flex-row items-center justify-between gap-2">
							<div class="flex flex-col min-w-0">
								<span class="font-semibold text-[14px] text-inkbase truncate">
									{{ member.employee_name }}
								</span>
								<span class="text-[11px] text-ink-600 truncate">
									{{ member.designation }}
								</span>
							</div>
							<span class="m-chip flex-none" :class="statusChipClass(member.status)">
								{{ __(member.status) }}
							</span>
						</div>
						<span class="text-[11px] text-ink-600 mt-1.5">{{ summaryLine(member) }}</span>

						<!-- expanded detail -->
						<div
							v-if="expandedRow === member.employee"
							class="flex flex-col gap-1 mt-2.5 pt-2.5 border-t border-divider text-[11px] text-ink-600"
						>
							<span v-if="member.shift">
								{{ __("Shift") }}: {{ member.shift }} ·
								{{ formatTime(member.shift_start) }}–{{ formatTime(member.shift_end) }}
							</span>
							<span>
								{{ __("First in") }}: {{ formatPunch(member.first_in) }} ·
								{{ __("Last out") }}: {{ formatPunch(member.last_out) }}
							</span>
							<span v-if="member.leave_type">
								{{ __(member.leave_type, null, "Leave Type") }}
								<template v-if="member.half_day">({{ __("Half Day") }})</template>
								· {{ __("until") }} {{ dayjs(member.leave_until).format("D MMM") }}
							</span>
						</div>
					</div>
				</div>

				<EmptyState
					:message="__('No direct reports found')"
					v-else-if="!teamStatus.loading"
				/>

				<div v-if="teamStatus.loading" class="flex mt-2 items-center justify-center">
					<LoadingIndicator class="w-8 h-8 text-accent" />
				</div>

				<span class="text-[10px] text-ink-600" v-if="teamStatus.data?.members?.length">
					{{ __("You see your direct reports. Pull the day arrows to browse other dates.") }}
				</span>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { FeatherIcon, LoadingIndicator } from "frappe-ui"
import { computed, inject, ref } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import EmptyState from "@/components/EmptyState.vue"
import { teamManagers, teamStatus } from "@/data/team"

const __ = inject("$translate")
const dayjs = inject("$dayjs")

const selectedDate = ref(dayjs().format("YYYY-MM-DD"))
const selectedManager = ref("")
const expandedRow = ref(null)

function fetchDay() {
	expandedRow.value = null
	teamStatus.fetch({
		date: selectedDate.value,
		manager: selectedManager.value || undefined,
	})
}
fetchDay()

function changeDay(delta) {
	selectedDate.value = dayjs(selectedDate.value).add(delta, "day").format("YYYY-MM-DD")
	expandedRow.value = null
	fetchDay()
}

function toggleRow(employee) {
	expandedRow.value = expandedRow.value === employee ? null : employee
}

const dayLabel = computed(() => {
	const day = dayjs(selectedDate.value)
	const prefix = day.isSame(dayjs(), "day") ? `${__("Today")} · ` : ""
	return `${prefix}${day.format("ddd D MMM")}`
})

const summaryTiles = computed(() => {
	const summary = teamStatus.data?.summary || {}
	// __("Present"), __("On Leave"), __("Not In Yet"), __("Absent")
	return [
		{ label: __("Present"), count: summary["Present"] || 0 },
		{ label: __("On Leave"), count: summary["On Leave"] || 0 },
		{ label: __("Not In Yet"), count: summary["Not In Yet"] || 0 },
		{ label: __("Absent"), count: summary["Absent"] || 0 },
	]
})

// app chip semantics (see LeaveRequestItem): solid = demands attention,
// outline = confirmed good, muted = neutral. The DS has no red variant.
function statusChipClass(status) {
	return (
		{
			Present: "m-chip-outline",
			Absent: "m-chip-solid",
		}[status] || "m-chip-muted"
	)
}

function formatPunch(value) {
	return value ? dayjs(value).format("HH:mm") : "—"
}

function formatTime(value) {
	// server sends "HH:MM:SS" strings
	return value ? value.slice(0, 5) : "—"
}

function summaryLine(member) {
	if (member.status === "On Leave") {
		const type = __(member.leave_type, null, "Leave Type")
		return `${type} · ${__("until")} ${dayjs(member.leave_until).format("D MMM")}`
	}
	if (member.first_in || member.last_out) {
		return `${__("IN")} ${formatPunch(member.first_in)} · ${__("OUT")} ${formatPunch(member.last_out)}`
	}
	if (member.status === "Not In Yet" && member.shift_start) {
		return `${__("Shift")} ${formatTime(member.shift_start)}–${formatTime(member.shift_end)} · ${__("no punch yet")}`
	}
	if (member.status === "Absent") {
		return __("No punch · no leave filed")
	}
	return __(member.status)
}
</script>
