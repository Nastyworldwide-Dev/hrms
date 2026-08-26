<template>
	<BaseLayout :pageTitle="__('Team')">
		<template #body>
			<div class="flex flex-col gap-5 w-full max-w-content-column-lg px-4 pt-[18px] pb-24 lg:p-7">
				<!-- HR-only team selector: grouped by department, searchable,
				     "My team" pinned first, team size beside each manager
				     (HR request 2026-08-19; options built by utils/team.js,
				     pinned by tests/manager-options.test.mjs) -->
				<div v-if="teamManagers.data?.length" class="flex flex-row items-center gap-2">
					<span class="g-eyebrow flex-none">{{ __("Team of") }}</span>
					<Autocomplete
						class="flex-1 min-w-0"
						:options="managerOptions"
						:modelValue="selectedOption"
						:placeholder="__('My team')"
						@update:modelValue="onManagerPicked"
					/>
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
					<!-- data-visual-mask: defaults to today, so "TODAY · FRI 21 AUG"
					     becomes "TODAY · SUN 23 AUG" overnight. -->
					<span class="g-datenav__label" data-visual-mask>
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
						<span class="font-sans font-extrabold text-stat-number leading-none text-inkbase">
							{{ tile.count }}
						</span>
						<span class="g-eyebrow">
							{{ tile.label }}
						</span>
					</div>
				</div>

				<!-- member rows, sectioned by department. Presentation only: the
				     member SET is exactly the reports_to team the server returned —
				     frontend/tests/team-grouping.test.mjs pins that grouping can
				     never add, drop, or leak a member. -->
				<div
					class="flex flex-col border-t-2 border-divider"
					v-if="teamStatus.data?.members?.length"
				>
					<template v-for="group in departmentGroups" :key="group.department">
						<div class="g-eyebrow px-3 pt-4 pb-1.5">
							{{ group.department }} ({{ group.members.length }})
						</div>
						<div
							v-for="member in group.members"
							:key="member.employee"
							class="flex flex-col bg-surface border-b border-divider p-3 cursor-pointer"
							@click="toggleRow(member.employee)"
						>
							<div class="flex flex-row items-center justify-between gap-2">
								<div class="flex flex-col min-w-0">
									<span class="font-semibold text-panel-title text-inkbase truncate">
										{{ member.employee_name }}
									</span>
									<span class="text-kra-label text-ink-600 truncate">
										{{ member.designation }}
									</span>
								</div>
								<GStatusChip
									class="flex-none"
									:status="member.status"
									:label="__(member.status)"
								/>
							</div>
							<span class="text-kra-label text-ink-600 mt-1.5">{{ summaryLine(member) }}</span>

							<!-- expanded detail -->
							<div
								v-if="expandedRow === member.employee"
								class="flex flex-col gap-1 mt-2.5 pt-2.5 border-t border-divider text-kra-label text-ink-600"
							>
								<span v-if="member.shift">
									{{ __("Shift") }}: {{ member.shift }} · {{ formatTime(member.shift_start) }}–{{
										formatTime(member.shift_end)
									}}
								</span>
								<span>
									{{ __("First in") }}: {{ formatPunch(member.first_in) }} · {{ __("Last out") }}:
									{{ formatPunch(member.last_out) }}
								</span>
								<span v-if="member.leave_type">
									{{ __(member.leave_type, null, "Leave Type") }}
									<template v-if="member.half_day">({{ __("Half Day") }})</template>
									· {{ __("until") }} {{ dayjs(member.leave_until).format("D MMM") }}
								</span>
							</div>
						</div>
					</template>
				</div>

				<GEmptyState
					v-else-if="!teamStatus.loading"
					:title="__('Nothing waiting on you')"
					:body="__('Approvals will appear here when your team submits')"
				/>

				<div v-if="teamStatus.loading" class="flex mt-2 items-center justify-center">
					<GSkeleton height="14px" width="42%" />
				</div>

				<span class="text-caption text-ink-600" v-if="teamStatus.data?.members?.length">
					{{ __("You see your direct reports. Pull the day arrows to browse other dates.") }}
				</span>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import { Autocomplete, FeatherIcon } from "frappe-ui"
import { computed, inject, ref } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import { teamManagers, teamStatus } from "@/data/team"
import { buildManagerOptions, groupByDepartment } from "@/utils/team"

const __ = inject("$translate")
const dayjs = inject("$dayjs")

const selectedDate = ref(dayjs().format("YYYY-MM-DD"))
const selectedManager = ref("")
const selectedOption = ref(null) // null renders the placeholder: "My team"
const managerOptions = computed(() => buildManagerOptions(teamManagers.data || [], __("My team")))

function onManagerPicked(option) {
	console.info("[TeamDashboard] team selected:", option?.label || "My team")
	selectedOption.value = option
	selectedManager.value = option?.value || ""
	fetchDay()
}

const departmentGroups = computed(() => groupByDepartment(teamStatus.data?.members))

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
		return `${__("IN")} ${formatPunch(member.first_in)} · ${__("OUT")} ${formatPunch(
			member.last_out
		)}`
	}
	if (member.status === "Not In Yet" && member.shift_start) {
		return `${__("Shift")} ${formatTime(member.shift_start)}–${formatTime(
			member.shift_end
		)} · ${__("no punch yet")}`
	}
	if (member.status === "Absent") {
		return __("No punch · no leave filed")
	}
	return __(member.status)
}
</script>
