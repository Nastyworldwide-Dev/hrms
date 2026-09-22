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
				<!-- What the day WAS. The shift window is here because "I was
				     marked absent" and "I was marked absent on a shift I was
				     not assigned" are different conversations. -->
				<GMetaGrid :cells="facts" />

				<template v-if="me.punches.length">
					<div class="g-eyebrow">{{ __("Your taps") }}</div>
					<GListPanel>
						<GListRow
							v-for="(punch, index) in me.punches"
							:key="index"
							:label="punchTime(punch)"
							:sublabel="punch.skipped ? __('Set aside by HR') : null"
							:chevron="false"
						/>
					</GListPanel>
				</template>
				<GEmptyState
					v-else
					:title="__('No taps on this day')"
					:body="__('If you worked, ask for the day to be fixed below.')"
				/>

				<!-- WHO IS OFF — approver and above. Type, never reason. -->
				<template v-if="teamOff">
					<div class="g-eyebrow">{{ __("Who is off") }}</div>
					<GListPanel v-if="teamOff.length">
						<GListRow
							v-for="row in teamOff"
							:key="row.employee"
							:label="row.name"
							:sublabel="offLabel(row)"
							:chevron="false"
						/>
					</GListPanel>
					<GEmptyState v-else :title="__('Everyone is in')" />
				</template>

				<!-- COVERAGE — the number a manager opens a calendar for. -->
				<GMetaGrid v-if="coverage" :cells="coverageCells" />

				<div class="flex flex-col gap-2">
					<GGhostButton :label="__('Request a fix for this day')" @click="fixDay" />
					<GGhostButton
						v-if="me.ot_hours > 0"
						:label="__('Claim this overtime')"
						@click="claimOt"
					/>
				</div>
			</template>
		</div>
	</GModal>
</template>

<script setup>
import { computed, inject, watch } from "vue"
import { useRouter } from "vue-router"

import GEmptyState from "@/components/glass/GEmptyState.vue"
import GGhostButton from "@/components/glass/GGhostButton.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GMetaGrid from "@/components/glass/GMetaGrid.vue"
import GModal from "@/components/glass/GModal.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import ResourceError from "@/components/ResourceError.vue"

import { daySheet } from "@/data/calendar"

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
const teamOff = computed(() => daySheet.data?.team_off)
const coverage = computed(() => daySheet.data?.coverage)

const heading = computed(() => (props.date ? $dayjs(props.date).format("dddd, D MMMM") : ""))

function punchTime(punch) {
	return $dayjs(punch.time).format("HH:mm") + (punch.log_type ? ` · ${punch.log_type}` : "")
}

function offLabel(row) {
	// The TYPE, never the reason (owner's ruling). Half-day is part of the
	// type's meaning for anybody planning cover.
	return row.half_day ? __("{0} · half day", [row.leave_type]) : row.leave_type
}

const facts = computed(() => {
	const day = me.value
	if (!day) return []
	return [
		{ k: __("Status"), v: day.status || __("Not marked") },
		{
			k: __("Shift"),
			v: day.shift ? `${trimSeconds(day.shift.start)}–${trimSeconds(day.shift.end)}` : __("None"),
		},
		{ k: __("Worked"), v: day.worked_hours ? __("{0} h", [day.worked_hours.toFixed(2)]) : "—" },
		{ k: __("Overtime"), v: day.ot_hours ? __("{0} h", [day.ot_hours.toFixed(2)]) : "—" },
	]
})

const coverageCells = computed(() => {
	const row = coverage.value
	if (!row) return []
	return [
		{ k: __("In"), v: String(row.present) },
		{ k: __("On leave"), v: String(row.on_leave) },
		{ k: __("Absent"), v: String(row.absent) },
		// The number that costs money on a past day: nobody has said anything
		// about these people at all.
		{ k: __("Not marked"), v: String(row.unmarked) },
	]
})

function trimSeconds(value) {
	return String(value || "").slice(0, 5)
}

function fixDay() {
	// Pre-filled with the date, because the whole reason to open a day sheet
	// and then a form is that the form already knows which day.
	router.push({ name: "AttendanceRequestFormView", query: { date: props.date } })
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
