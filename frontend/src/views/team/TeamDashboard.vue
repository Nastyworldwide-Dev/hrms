<template>
	<BaseLayout :pageTitle="__('Team')">
		<template #body>
			<div
				class="flex flex-col gap-5 w-full max-w-content-column-lg mx-auto px-4 pt-4 pb-24 lg:p-7"
			>
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

				<!-- Month picker: the Attendance calendar card, reused. The old
				     prev/next day arrows meant browsing a week took seven taps; a
				     month grid is one. A team has no single per-day status, so the
				     grid only marks the selected day and today (utils/team.js,
				     pinned by tests/team-calendar-days.test.mjs). -->
				<GCalendar
					:title="`${firstOfMonth.format('MMMM')} ${firstOfMonth.format('YYYY')}`"
					:days="calendarDays"
					:leading-blanks="firstOfMonth.get('d')"
					:weekdays="DAYS"
					:legend="LEGEND"
					@select="pickDay"
				>
					<template #action>
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

				<div class="flex flex-row items-center justify-between gap-2">
					<!-- data-visual-mask: defaults to today, so "TODAY · FRI 21 AUG"
					     becomes "TODAY · SUN 23 AUG" overnight. -->
					<span class="g-datenav__label" data-visual-mask>
						{{ dayLabel }}
					</span>
					<router-link
						v-if="teamStatus.data?.members?.length"
						:to="{ name: 'TeamRosterView' }"
						class="g-seclink g-focusable text-kra-label text-accent-ink underline underline-offset-link"
					>
						{{ __("Open team roster") }}
					</router-link>
				</div>

				<ResourceError :resource="teamStatus" what="your team's status" />
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
							{{ departmentLabel(group.department) }} ({{ group.members.length }})
						</div>
						<div
							v-for="member in group.members"
							:key="member.employee"
							class="g-focusable flex flex-col bg-surface border-b border-divider p-3 cursor-pointer"
							role="button"
							tabindex="0"
							:aria-expanded="String(expandedRow === member.employee)"
							@click="toggleRow(member.employee)"
							@keydown.enter.prevent="toggleRow(member.employee)"
							@keydown.space.prevent="toggleRow(member.employee)"
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
									<template v-if="member.half_day">({{ __("Half day") }})</template>
									· {{ __("until") }} {{ dayjs(member.leave_until).format("D MMM") }}
								</span>
							</div>
						</div>
					</template>
				</div>

				<!-- TWO different empties, and saying the wrong one is a false
				     statement about somebody's job. An employee who is nobody's
				     manager was told "approvals will appear here when your team
				     submits" — about a team they do not have — because the
				     server returned the same payload for both cases. It now
				     says which, and this renders the truth rather than the
				     friendlier of the two.

				     The role is NEVER decided here (revamp P5): `entitled` is
				     the server's answer, and the screen has no opinion. -->
				<GEmptyState
					v-else-if="notEntitled"
					:title="__('You do not have a team here')"
					:body="
						__(
							'This screen shows the people who report to you. Ask HR if you think that is wrong.'
						)
					"
				/>
				<GEmptyState
					v-else-if="!teamStatus.loading && !teamStatus.error"
					:title="__('Nobody on your team today')"
					:body="__('Pick another day on the calendar, or check back tomorrow.')"
				/>

				<div v-if="teamStatus.loading" class="flex mt-2 items-center justify-center">
					<GSkeleton height="14px" width="42%" />
				</div>

				<span class="text-caption text-ink-600" v-if="teamStatus.data?.members?.length">
					{{ __("You see your direct reports. Tap a day on the calendar to browse other dates.") }}
				</span>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import GCalendar from "@/components/glass/GCalendar.vue"
import { Autocomplete } from "frappe-ui"
import { computed, inject, ref } from "vue"
import { useRoute } from "vue-router"
import { dateFromRoute } from "@/utils/dateFromRoute"
import { clockTime } from "@/utils/daySheet"

import BaseLayout from "@/components/BaseLayout.vue"
import { teamManagers, teamStatus } from "@/data/team"
import { buildManagerOptions, buildTeamCalendarDays, groupByDepartment } from "@/utils/team"
import { departmentLabel } from "@/utils/departmentLabel"

const __ = inject("$translate")
const dayjs = inject("$dayjs")

// ?date= comes from the Calendar day sheet's team line (owner ruling 1):
// the door opens on the day it summarised.
const route = useRoute()
const askedDate = dateFromRoute(route.query)
const selectedDate = ref(askedDate || dayjs().format("YYYY-MM-DD"))
const firstOfMonth = ref(dayjs(selectedDate.value).date(1).startOf("D"))

const calendarDays = computed(() =>
	buildTeamCalendarDays(
		firstOfMonth.value.format("YYYY-MM-DD"),
		selectedDate.value,
		dayjs().format("YYYY-MM-DD")
	)
)

const getDayAbbr = (s) => s.trim().slice(0, 3)
const DAYS = [
	getDayAbbr(__("Sunday")),
	getDayAbbr(__("Monday")),
	getDayAbbr(__("Tuesday")),
	getDayAbbr(__("Wednesday")),
	getDayAbbr(__("Thursday")),
	getDayAbbr(__("Friday")),
	getDayAbbr(__("Saturday")),
]
// the legend names the states the grid can show, and is the source of each
// day cell's spoken state (GCalendar)
const LEGEND = [
	{ state: "selected", label: __("Selected day") },
	{ state: "today", label: __("Today") },
]
const selectedManager = ref("")
//: The SERVER's answer to "do you have a team at all" (revamp P5). The screen
//: never decides this — no role check, no reports_to lookup — so there is
//: nothing here that could disagree with the backend's rules.
//:
//: `=== false` deliberately, not `!entitled`: while the payload is absent the
//: flag is undefined, and treating that as "not entitled" would flash "you do
//: not have a team" at every manager on every load.
const notEntitled = computed(() => teamStatus.data?.entitled === false)

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

function pickDay(day) {
	selectedDate.value = firstOfMonth.value.date(day).format("YYYY-MM-DD")
	console.info("[TeamDashboard] day picked:", selectedDate.value)
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

function formatPunch(value) {
	return value ? dayjs(value).format("HH:mm") : "—"
}

function formatTime(value) {
	// "9:00:00" for a one-digit hour: read by value, not by position (live
	// audit 23 Sep, the "9:00:" shift time).
	return clockTime(value) || "—"
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
