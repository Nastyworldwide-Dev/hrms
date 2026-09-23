<!--
  One day, in words (revamp §4, slice C3).

  The grid says what KIND of day it was; this says what actually happened. It
  is the only place on the calendar that renders sentences, which is the whole
  reason the tiles can stay legible.

  EVERY SECTION IS THE SERVER'S ANSWER. This component renders what arrives
  and holds no role logic at all: an employee gets their own day, an approver
  additionally gets who in their line is off, a manager gets the coverage
  line. There is nothing here to keep in step with the backend's rules, and
  nothing here that could disagree with them.

  A section that did not arrive renders NOTHING — not an empty state saying
  "no team". An employee who is nobody's approver does not have a team; a
  card telling them their team is all present would be a false statement.
-->
<template>
	<GModal :is-open="open" :title="heading" @did-dismiss="$emit('close')">
		<div class="flex flex-col gap-4">
			<ResourceError :resource="daySheet" what="this day" />

			<template v-if="daySheet.loading && !me">
				<GSkeleton height="18px" width="50%" />
				<GSkeleton height="120px" />
			</template>

			<template v-else-if="me">
				<!-- One line of shift, the taps, the hours (approved Calendar plan
				     §4). No explaining paragraph. -->
				<p class="text-card-title text-ink-600">{{ shiftLine }}</p>

				<GListPanel v-if="me.punches.length">
					<GListRow
						v-for="(punch, index) in me.punches"
						:key="index"
						:label="punchLabel(punch)"
						:sublabel="punch.skipped ? __('Set aside by HR') : null"
						:chevron="false"
					/>
				</GListPanel>
				<p v-else class="text-card-title text-ink-600">
					{{ __("You didn't check in this day.") }}
				</p>

				<p v-if="hoursLine" class="text-card-title text-inkbase">{{ hoursLine }}</p>

				<!-- ONE team line for managers and team leads, their direct team
				     only (owner ruling 1, 23 Sep; AUDIT-PLAN "Team line"). The line
				     is the door; the Team page, for this date, has the names and the
				     leave TYPE, never the reason. -->
				<GListPanel v-if="teamSummary">
					<GListRow :label="teamSummary" @click="openTeam" />
				</GListPanel>

				<!-- Exactly one main action, chosen by the day, or one line saying
				     there is nothing to do (D10: it offered "fix" on every day). -->
				<GButton v-if="action.kind === 'claim'" :label="__(action.label)" @click="claimOt" />
				<GButton v-else-if="action.kind === 'fix'" :label="__(action.label)" @click="fixDay" />
				<p v-else-if="action.note" class="text-card-title text-ink-600">{{ __(action.note) }}</p>
			</template>
		</div>
	</GModal>
</template>

<script setup>
import { computed, inject, watch } from "vue"
import { useRouter } from "vue-router"

import { teamLine } from "@/utils/teamLine"

import GButton from "@/components/glass/GButton.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GModal from "@/components/glass/GModal.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import ResourceError from "@/components/ResourceError.vue"

import { daySheet } from "@/data/calendar"
import { dayAction, hoursAsTime, tapWord, clockTime } from "@/utils/daySheet"

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
const coverage = computed(() => daySheet.data?.coverage)
const teamSummary = computed(() =>
	teamLine(coverage.value, props.date, $dayjs().format("YYYY-MM-DD"), __)
)

const heading = computed(() => (props.date ? $dayjs(props.date).format("dddd, D MMMM") : ""))

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

//: "In 09:31", never the raw "IN" (D12).
function punchLabel(punch) {
	const word = tapWord(punch.log_type)
	const time = $dayjs(punch.time).format("HH:mm")
	return word ? `${__(word)} ${time}` : time
}

function fixDay() {
	// Pre-filled with the date, because the whole reason to open a day sheet
	// and then a form is that the form already knows which day.
	router.push({ name: "AttendanceRequestFormView", query: { date: props.date } })
}

function openTeam() {
	console.info("[DaySheet] opening team for", props.date)
	router.push({ name: "TeamView", query: { date: props.date } })
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
