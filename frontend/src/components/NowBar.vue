<!--
  The line at the top of Home (revamp §2).

  What it replaces: "Last check-out was at 08:17 pm". True, and it made the
  reader do the rest of the work — am I on shift, how long have I been in,
  does today's shift start yet. Somebody standing at a door with a phone in
  one hand should not be doing arithmetic.

  IT ALWAYS RENDERS. The first build made every part conditional, so an
  employee with no shift assigned and no open punch got an empty bar — and
  Home opened on the same "Last check-out was at 08:17 pm" it always had.
  That shipped on 23 September and it was the first thing the owner saw. A
  status line whose job is to say what is true now does not get to say
  nothing: "No shift today" is an answer, and an empty space is not.

  THE STATE IS THE SERVER'S WORD. Four of them — working, done, before, off —
  and the copy lives with the rule that chooses it, so the screen cannot
  disagree with the reason.

  THE TIMER TICKS once a minute, which is the resolution the number is stated
  at. A per-second interval would re-render Home sixty times for a digit
  nobody is watching, and a session that says "6h 12m" and then stops reads
  as the app having lost track.
-->
<template>
	<div
		class="g-now"
		:class="[
			`g-now--${stateKey}`,
			{ 'g-now--past': gauge && gauge.level !== 'working', 'g-now--forgot': gauge?.level === 'forgot' },
		]"
	>
		<!-- The date is content, so it sits with today's content, once — not in
		     the header in place of the Nadi mark (owner, 23 Sep; DETAIL §1.3). -->
		<p class="g-now__date" data-visual-mask>{{ today }}</p>
		<!-- Four states (D6): a skeleton while the first read is in flight, so
		     the bar keeps its space without claiming "No shift today" early. -->
		<div v-if="pending" class="g-now__row">
			<GSkeleton width="60%" height="18px" />
		</div>
		<div v-else class="g-now__row">
			<span class="g-now__dot" aria-hidden="true" />
			<p class="g-now__state">
				{{ stateWord }}
				<!-- The running time rolls to its new value, as the Clock app's
				     digits do (Apple: content replace), instead of snapping. -->
				<Transition name="g-roll" mode="out-in">
					<span v-if="stateClock" :key="stateClock" class="g-now__clock">{{ stateClock }}</span>
				</Transition>
			</p>
		</div>
		<p v-if="detail" class="g-now__detail">{{ detail }}</p>
		<!-- The shift as a gauge while you are checked in (the owner's "Apple
		     way" card): Apple's capacity gauge, both ends labelled, the fill
		     turning orange past the end (Apple, gauges). -->
		<div
			v-if="gauge"
			class="g-now__gauge"
			role="meter"
			:aria-label="__('Shift progress')"
			aria-valuemin="0"
			aria-valuemax="100"
			:aria-valuenow="Math.round(gauge.fraction * 100)"
			:aria-valuetext="gaugeMiddle"
		>
			<div class="g-now__gauge-track">
				<div class="g-now__gauge-fill" :style="{ width: `${gauge.fraction * 100}%` }" />
			</div>
			<div class="g-now__gauge-ends" aria-hidden="true">
				<span>{{ clockTime(shift.start) }}</span>
				<b>{{ gaugeMiddle }}</b>
				<span>{{ clockTime(shift.end) }}</span>
			</div>
		</div>
		<!-- Long past the shift end: probably a forgotten check-out. Said once,
		     with one wiggle so it is not missed (Apple: Wiggle, "a call to action
		     a person might overlook"); the fix is the card's own button below. -->
		<p v-if="gauge?.level === 'forgot'" class="g-now__forgot" role="status">
			{{ __("Your shift ended at {0}. Forgot to check out?", [clockTime(shift.end)]) }}
		</p>
		<!-- The shift line's place while pending (alpha.8 r3: it arrived after
		     the state and pushed the Check in button down 24 pt). -->
		<p v-else-if="pending" class="g-now__detail" aria-hidden="true">
			<GSkeleton width="45%" height="11px" />
		</p>
		<!-- The state changes without the employee doing anything — a shift
		     starts, a session passes an hour. Polite: not worth interrupting a
		     sentence that is already being read. -->
		<p class="sr-only" role="status">{{ stateLine }}{{ detail ? `. ${detail}` : "" }}</p>
	</div>
</template>

<script setup>
import { siteTime } from "@/utils/siteTime"
import { shiftGauge } from "@/utils/shiftGauge"
import { clockTime } from "@/utils/daySheet"
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from "vue"

import GSkeleton from "@/components/glass/GSkeleton.vue"
import { nowResource } from "@/data/now"

const __ = inject("$translate")
const $dayjs = inject("$dayjs")
const today = computed(() => $dayjs().format("dddd, D MMMM"))

//: Once a minute. The number is stated in minutes, so a faster tick re-renders
//: Home for a digit that has not changed.
const TICK_MS = 60_000

//: Bumped by the interval purely to re-run the elapsed computed. The time is
//: derived from the session's START, never accumulated — a counter that adds a
//: minute per tick drifts, and drifts most while the phone is asleep, which is
//: exactly when nobody can see it going wrong.
const tick = ref(0)
let timer = null

const data = computed(() => nowResource.data || {})
const session = computed(() => data.value.session)
const shift = computed(() => data.value.shift)

//: Falls back to "off" rather than to nothing. While the payload is in flight
//: the bar still occupies its space, so Home does not jump when it lands —
//: that jump is a layout shift (CLS) on the first screen of the app.
const stateKey = computed(() => data.value.state?.key || "off")

//: First read in flight with nothing (not even a cached copy) to show.
const pending = computed(() => Boolean(nowResource.loading && !data.value.state))

const elapsed = computed(() => {
	void tick.value // read it so the interval re-evaluates this
	if (!session.value?.since) return ""
	// Safari parses "2026-09-22 19:00:00" as Invalid Date — the defect
	// CheckInPanel already carries a note about — and "NaNm" at the top of
	// Home is worse than no number.
	// On the SITE clock: a device in another zone read "since" as its own
	// wall time and was off by the zone gap (alpha.5 audit).
	const started = siteTime(session.value.since)
	if (!started.isValid()) return ""
	const minutes = Math.max(0, Math.floor((Date.now() - started.valueOf()) / 60000))
	const hours = Math.floor(minutes / 60)
	return hours > 0 ? __("{0}h {1}m", [hours, minutes % 60]) : __("{0}m", [minutes])
})

const stateLine = computed(() => {
	const label = data.value.state?.label
	// A failed read is not "no shift": that would be a false answer at the top
	// of Home. Say we could not load, and how to retry (D6).
	if (!label && nowResource.error) {
		console.warn("[NowBar] today's state failed to load", nowResource.error)
		return __("We couldn't load today. Pull down to try again.")
	}
	if (!label) return __("No shift today")
	// The running time belongs IN the state line, not under it: "Working ·
	// 3h 12m" is one fact, and splitting it across two lines makes the reader
	// join them.
	return stateKey.value === "working" && elapsed.value
		? __("{0} · {1}", [__(label), elapsed.value])
		: __(label)
})

const detail = computed(() => {
	if (!data.value.state && nowResource.error) return ""
	// The shift window, when there is one — that is the thing a person checks
	// the bar for after the state itself.
	if (shift.value) {
		return __("{0} · {1}–{2}", [
			shift.value.shift,
			clockTime(shift.value.start),
			clockTime(shift.value.end),
		])
	}
	// No shift, but they finished today: say when, because that is the only
	// other fact the bar has and it is the one the old line carried.
	if (stateKey.value === "done" && data.value.last_out) {
		return __("Checked out at {0}", [$dayjs(data.value.last_out).format("h:mm a")])
	}
	return ""
})

//: The minute of the employee's day. The server sends their wall clock
//: (`time`, "HH:MM", employee_now) — the one clock the shift window is in —
//: and this advances it by the real time since that answer landed. A device in
//: another zone reading its own clock put the gauge hours out (measured: 9h 44m
//: "left" at 13:46 on a 09:00-18:00 shift).
const answeredAt = ref(Date.now())
watch(
	() => data.value.time,
	() => (answeredAt.value = Date.now())
)
const nowMin = computed(() => {
	void tick.value
	const [h, m] = String(data.value.time || "").split(":").map(Number)
	if (!Number.isFinite(h) || !Number.isFinite(m)) return null
	return (h * 60 + m + Math.floor((Date.now() - answeredAt.value) / 60000)) % (24 * 60)
})

//: Only while checked in with a shift window: that is when "how far through"
//: means something. Worked out from the window, never counted.
const gauge = computed(() =>
	stateKey.value === "working" && shift.value && nowMin.value !== null
		? shiftGauge({ start: shift.value.start, end: shift.value.end, nowMin: nowMin.value })
		: null
)

const gaugeMiddle = computed(() => {
	if (!gauge.value) return ""
	const span = (m) => (m >= 60 ? __("{0}h {1}m", [Math.floor(m / 60), m % 60]) : __("{0}m", [m]))
	return gauge.value.pastMin > 0
		? __("{0} past the end", [span(gauge.value.pastMin)])
		: __("{0} left", [span(gauge.value.leftMin)])
})


//: The state line in two parts, so the running time can roll on its own.
const stateClock = computed(() =>
	stateKey.value === "working" && elapsed.value && stateLine.value.endsWith(elapsed.value)
		? elapsed.value
		: ""
)
const stateWord = computed(() => {
	const line = stateLine.value
	return stateClock.value ? line.slice(0, line.length - stateClock.value.length) : line
})

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
