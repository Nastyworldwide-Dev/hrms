<!--
  The one line at the top of Home (revamp §2).

  What it replaces: "Last check-out was at 08:17 pm". True, and it made the
  reader do the rest of the work — am I on shift, how long have I been in,
  does today's shift start yet. Somebody standing at a door with a phone in
  one hand should not be doing arithmetic.

  THREE FACTS, in the order a person needs them: what shift today is, whether
  they are currently in, and for how long. Each disappears when it does not
  apply, so an employee with no shift assigned sees a shorter line rather than
  "Shift: none".

  THE TIMER TICKS. A session that says "6h 12m" and then stops is worse than
  no timer — it reads as the app having lost track. It updates once a minute,
  which is the resolution the number is stated at; a per-second interval would
  re-render Home sixty times for a digit nobody is watching.
-->
<template>
	<div v-if="hasAnything" class="flex flex-col gap-1">
		<p v-if="sessionText" class="text-panel-title text-inkbase">{{ sessionText }}</p>
		<p v-if="shiftText" class="text-caption text-ink-600">{{ shiftText }}</p>
		<!-- The state changes without the employee doing anything — a shift
		     starts, a session passes an hour. Polite: it is not worth
		     interrupting a sentence for. -->
		<p class="sr-only" role="status">{{ sessionText }}</p>
	</div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, onMounted, ref } from "vue"

import { nowResource } from "@/data/now"

const __ = inject("$translate")

//: Once a minute. The number is stated in minutes, so a faster tick re-renders
//: Home for a digit that has not changed.
const TICK_MS = 60_000

//: Bumped by the interval purely to re-run the computed below. The elapsed
//: time is derived from the session's START, never accumulated — a counter
//: that adds a minute per tick drifts, and drifts most when the phone sleeps,
//: which is exactly when somebody is not watching.
const tick = ref(0)
let timer = null

const data = computed(() => nowResource.data || {})
const session = computed(() => data.value.session)
const shift = computed(() => data.value.shift)

const sessionText = computed(() => {
	// Read `tick` so the interval re-evaluates this.
	void tick.value
	if (!session.value?.since) return ""
	const started = new Date(String(session.value.since).replace(" ", "T"))
	if (Number.isNaN(started.getTime())) return ""
	const minutes = Math.max(0, Math.floor((Date.now() - started.getTime()) / 60000))
	const hours = Math.floor(minutes / 60)
	return hours > 0
		? __("Working · {0}h {1}m", [hours, minutes % 60])
		: __("Working · {0}m", [minutes])
})

const shiftText = computed(() => {
	if (!shift.value) return ""
	return __("{0} · {1}–{2}", [shift.value.shift, shift.value.start, shift.value.end])
})

const hasAnything = computed(() => Boolean(sessionText.value || shiftText.value))

onMounted(() => {
	nowResource.fetch()
	timer = setInterval(() => {
		tick.value += 1
	}, TICK_MS)
})

//: A timer left running writes to a ref nobody is rendering, on every screen
//: the employee visits after this one.
onBeforeUnmount(() => clearInterval(timer))
</script>
