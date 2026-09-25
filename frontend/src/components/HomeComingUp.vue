<!--
  HomeComingUp — "Coming up" on Home (owner-approved Home, 23 Sep 2026).

  The ONE next thing the employee has booked: approved leave, an approved
  trip, or a training they attend — "Annual leave · Mon 29 Sep ›". Never a
  reason; the server does not send one.

  ALWAYS renders. Nothing booked says so, and names the next public holiday
  from the employee's own holiday list when there is one:
  "Nothing booked. Next public holiday: Deepavali · Tue 20 Oct".
-->
<template>
	<div class="w-full">
		<p v-if="homeComingUp.error" class="text-caption text-ink-600">
			{{ __("Coming up could not be loaded. Pull down to try again.") }}
		</p>
		<template v-else>
			<GListRow :label="label" :sublabel="sublabel" :tappable="Boolean(target)" @click="open">
				<template #icon>
					<component :is="icon" class="g-row-icon" />
				</template>
			</GListRow>
		</template>
	</div>
</template>

<script setup>
import { computed, inject, onMounted } from "vue"
import { useRouter } from "vue-router"
import { CalendarDays, GraduationCap, Palmtree, Plane } from "lucide-vue-next"

import GListRow from "@/components/glass/GListRow.vue"

import { homeComingUp } from "@/data/home"

const __ = inject("$translate")
const $dayjs = inject("$dayjs")
const router = useRouter()

//: Where a booked thing opens. Only leave has a list of its own in the PWA;
//: a trip or a training is a fact to know, not a row to open.
const TARGETS = { leave: "LeaveApplicationListView" }
const ICONS = { leave: Palmtree, travel: Plane, training: GraduationCap }

const next = computed(() => homeComingUp.data?.next || null)
const holiday = computed(() => homeComingUp.data?.holiday || null)
const target = computed(() => (next.value && TARGETS[next.value.kind]) || null)
const icon = computed(() => (next.value && ICONS[next.value.kind]) || CalendarDays)

const day = (value) => $dayjs(value).format("ddd D MMM")

//: The kind's own word. A leave type is the employee's own record and is shown
//: as named; "Trip" is ours, so it is translated.
function what(item) {
	if (item.kind === "travel") return __("Trip")
	return item.label
}

//: Title + subtitle, as an iOS row (alpha.8): one sentence wrapped to two
//: heading-sized lines on a phone.
const label = computed(() =>
	next.value ? `${what(next.value)} · ${day(next.value.date)}` : __("Nothing booked")
)
const sublabel = computed(() =>
	!next.value && holiday.value
		? __("Next public holiday: {0} · {1}", [holiday.value.label, day(holiday.value.date)])
		: ""
)

function open() {
	if (!target.value) return
	console.info("[HomeComingUp] open", { kind: next.value?.kind })
	router.push({ name: target.value })
}

onMounted(() => {
	homeComingUp.fetch()
})
</script>
