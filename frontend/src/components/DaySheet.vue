<!--
  One day, in words (revamp §4, slice C3).

  The grid says what KIND of day it was; this says what actually happened. It
  is the only place on the calendar that renders sentences, which is the whole
  reason the tiles can stay legible.

  EVERY SECTION IS THE SERVER'S ANSWER. This component renders what arrives
  and holds no role logic at all: an employee gets their own day, an approver
  additionally gets their direct team (the Team page's rows, 28 Sep 2026)
  with the coverage line. There is nothing here to keep in step with the backend's rules, and
  nothing here that could disagree with them.

  A section that did not arrive renders NOTHING — not an empty state saying
  "no team". An employee who is nobody's approver does not have a team; a
  card telling them their team is all present would be a false statement.
-->
<template>
	<GModal :is-open="open" :title="heading" @did-dismiss="$emit('close')">
		<div class="g-form-body">
			<ResourceError :resource="daySheet" what="this day" />

			<template v-if="daySheet.loading && !me">
				<GSkeleton height="18px" width="50%" />
				<GSkeleton height="120px" />
			</template>

			<template v-else-if="me">
				<!-- iOS sections (alpha.11: the audit, opening this sheet for the
				     first time, found three loose lines): the shift is the header
				     over the taps, the hours and any note are their footers. -->
				<section class="g-form-section">
					<h2 class="g-form-section__title">{{ shiftLine }}</h2>
					<GListPanel v-if="me.punches.length">
						<GListRow
							v-for="(punch, index) in me.punches"
							:key="index"
							:label="punchLabel(punch)"
							:sublabel="punch.skipped ? __('Set aside by HR') : null"
							:chevron="false"
						/>
					</GListPanel>
					<!-- A date that only holds a check-out from the night before:
					     where it counted, never a bare tap read as "In progress". -->
					<GListPanel v-else-if="(me.counted_elsewhere || []).length">
						<GListRow
							v-for="(tap, index) in me.counted_elsewhere"
							:key="index"
							:label="__('{0} {1}', [__(tapWord(tap.log_type)), $dayjs(tap.time).format('HH:mm')])"
							:sublabel="__('Counted on {0}', [$dayjs(tap.counted_on).format('ddd D MMM')])"
							:chevron="false"
						/>
					</GListPanel>
					<GListPanel v-else>
						<GListRow :label="__('You didn\'t check in this day.')" :tappable="false" />
					</GListPanel>
					<!-- Said once, under the taps (owner, 26 Sep 2026: "special
					     wording so it's clear it was cleared out"). -->
					<p v-if="me.punches.some((p) => p.next_day)" class="g-form-footer">
						{{ __("Worked past midnight: the check-out after 12 am counts on this day.") }}
					</p>
					<p v-if="hoursLine" class="g-form-footer">{{ hoursLine }}</p>
				</section>

				<!-- The team, ONCE (owner, 29 Sep 2026, after Hafiz's report: the
				     sheet said 6 and listed 5, and showed the team three times).
				     One heading with the day's count, then every name, grouped;
				     each group's number is the names under it. Managers and team
				     leads only: the server sends a team section to them alone. -->
				<template v-if="teamRows.length">
					<h2 class="g-form-section__title g-form-section__title--lead">{{ teamHeading }}</h2>
					<section v-for="group in teamGroups" :key="group.status" class="g-form-section">
						<h3 class="g-form-section__title">
							{{ __("{0} ({1})", [__(groupTitle(group.status)), group.members.length]) }}
						</h3>
						<GListPanel>
							<GListRow
								v-for="member in group.members"
								:key="member.employee"
								:label="member.employee_name"
								:sublabel="memberLine(member, __, lineFormat)"
								:chevron="false"
								:tappable="false"
							/>
						</GListPanel>
					</section>
					<!-- Planning shifts is a different job, so it is a door, not a list. -->
					<GListPanel>
						<GListRow
							:label="__('Open team roster')"
							:sublabel="__('Shifts for the week')"
							@click="openRoster"
						/>
					</GListPanel>
				</template>

				<!-- Exactly one main action, chosen by the day, or one line saying
				     there is nothing to do (D10: it offered "fix" on every day). -->
				<GButton v-if="action.kind === 'claim'" :label="__(action.label)" @click="claimOt" />
				<GButton v-else-if="action.kind === 'fix'" :label="__(action.label)" @click="fixDay" />
				<GButton
					v-else-if="action.kind === 'leave'"
					:label="__(action.label)"
					@click="askDayOff"
				/>
				<p v-else-if="action.note" class="g-form-footer">
					{{ __(action.note, action.noteArgs) }}
				</p>
			</template>
		</div>
	</GModal>
</template>

<script setup>
import { computed, inject, watch } from "vue"
import { useRouter } from "vue-router"

import { teamHeadingWords } from "@/utils/teamLine"
import { dayTeamGroups } from "@/utils/dayTeamGroups"
import { memberLine } from "@/utils/team"

import GButton from "@/components/glass/GButton.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GModal from "@/components/glass/GModal.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import ResourceError from "@/components/ResourceError.vue"

import { daySheet } from "@/data/calendar"
import { dayAction, dayStatusWord, hoursAsTime, tapWord, clockTime } from "@/utils/daySheet"

const props = defineProps({
	open: { type: Boolean, default: false },
	date: { type: String, default: "" },
})
//: `did-dismiss` rather than a custom close: GModal wraps ion-modal, and the
//: sheet can be dismissed by a swipe or by the backdrop as well as by a
//: button. Listening to the framework's own event is the only way to hear all
//: three, and a parent that misses one is left with `open` stuck true.
defineEmits(["close"])

const __ = inject("$translate")
const $dayjs = inject("$dayjs")
const router = useRouter()

const me = computed(() => daySheet.data?.me)
//: The day's team, grouped (utils/dayTeamGroups.js): every member, once.
const teamRows = computed(() => daySheet.data?.team || [])
const teamGroups = computed(() => dayTeamGroups(teamRows.value))
//: "Your team · 4 of 6 in": the heading over the names, never a second list.
const teamHeading = computed(() =>
	teamHeadingWords(daySheet.data?.coverage, props.date, $dayjs().format("YYYY-MM-DD"), __)
)

//: Group headings in the person's words, not the stored status.
const GROUP_TITLES = { Present: "In", "Not In Yet": "Not in yet", "On Leave": "On leave" }
function groupTitle(status) {
	return GROUP_TITLES[status] || status
}

const lineFormat = {
	punch: (value) => (value ? $dayjs(value).format("HH:mm") : "—"),
	time: (value) => clockTime(value) || "—",
	day: (value) => $dayjs(value).format("ddd D MMM"),
	shortDay: (value) => $dayjs(value).format("D MMM"),
}

//: "Wed 16 Sep · Worked": the date plus one status word (§4 rule 1). Short
//: date parts keep it on one line; no word until the day has loaded.
const heading = computed(() => {
	if (!props.date) return ""
	const date = $dayjs(props.date).format("ddd D MMM")
	const word = me.value ? dayStatusWord(me.value, $dayjs().format("YYYY-MM-DD")) : ""
	return word ? `${date} · ${__(word)}` : date
})

//: What the day needs: one action or a note (utils/daySheet.js).
const action = computed(() =>
	me.value ? dayAction(me.value, $dayjs().format("YYYY-MM-DD")) : { kind: "none", note: "" }
)

const shiftLine = computed(() => {
	const day = me.value
	if (!day) return ""
	if (day.status === "Holiday") return __("Rest day")
	if (!day.shift) return __("No shift")
	return `${day.shift.shift} · ${clockTime(day.shift.start)}–${clockTime(day.shift.end)}`
})

//: "8h 02m worked · 1h 30m overtime" — time, not decimals (D11).
const hoursLine = computed(() => {
	const day = me.value
	if (!day?.worked_hours) return ""
	const worked = __("{0} worked", [hoursAsTime(day.worked_hours)])
	return day.ot_hours > 0
		? `${worked} · ${__("{0} overtime", [hoursAsTime(day.ot_hours)])}`
		: worked
})

//: "In 09:31", never the raw "IN" (D12); "Out 01:41 · next day" after midnight.
function punchLabel(punch) {
	const word = tapWord(punch.log_type)
	const time = $dayjs(punch.time).format("HH:mm")
	const label = word ? `${__(word)} ${time}` : time
	return punch.next_day ? `${label} · ${__("next day")}` : label
}

function fixDay() {
	// Pre-filled with the date, because the whole reason to open a day sheet
	// and then a form is that the form already knows which day.
	router.push({ name: "AttendanceRequestFormView", query: { date: props.date } })
}

function openRoster() {
	console.info("[DaySheet] opening team roster from", props.date)
	router.push({ name: "TeamRosterView" })
}

//: A future work day: the leave form, already on that date (§4 row 13).
function askDayOff() {
	router.push({ name: "LeaveApplicationFormView", query: { date: props.date } })
}

function claimOt() {
	router.push({ name: "OTRequestFormView", query: { date: props.date } })
}

watch(
	() => [props.open, props.date],
	([open, date]) => {
		if (open && date) daySheet.fetch({ date })
	},
	{ immediate: true }
)
</script>
