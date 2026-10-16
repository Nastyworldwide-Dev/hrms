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
			{
				'g-now--past': gauge && gauge.level !== 'working',
				'g-now--forgot': gauge?.level === 'forgot',
			},
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
				<span>{{ leaveHHMM || clockTime(shift.end) }}</span>
			</div>
		</div>
		<!-- Long past the shift end: probably a forgotten check-out. Said once,
		     with one wiggle so it is not missed (Apple: Wiggle, "a call to action
		     a person might overlook"); the fix is the card's own button below. -->
		<p v-if="gauge?.level === 'forgot'" class="g-now__forgot" role="status">
			{{
				__("You were due to leave at {0}. Forgot to check out?", [leaveAt || clockTime(shift.end)])
			}}
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
		<!-- The time slip, last on the card (owner, 14 Oct 2026). Its word is the server's
		     (time_slip.status); the sheet's clock check was only a hint. -->
		<p v-if="slipLine" class="g-now__slip" data-visual-mask>
			<span>{{ __("Time slip") }} ·</span>
			<span class="g-badge" :class="`g-chip--${slipLine.chip}`">{{ slipLine.text }}</span>
		</p>
		<button
			v-if="slipNeedsFile"
			type="button"
			class="g-now__slip-add g-focusable"
			@click="slipOpen = true"
		>
			{{ __("Add the file to your time slip") }}
		</button>
		<button
			v-else-if="slipOffered"
			type="button"
			class="g-now__slip-add g-focusable"
			@click="slipOpen = true"
		>
			{{ __("Late today? Add a time slip") }}
		</button>
	</div>

	<GModal :is-open="slipOpen" :title="__('Time slip')" @did-dismiss="closeSlip">
		<div class="g-form-body">
			<section class="g-form-section">
				<TimeSlipFields v-model:file="slipFile" />
				<p v-if="slipNeedsFile" class="g-form-footer">
					{{ __("Your time slip is saved. Add its file so your approver can see it.") }}
				</p>
				<p v-else class="g-form-footer">
					{{ __("Your approver is asked to approve it. If they do, today is not marked late.") }}
				</p>
			</section>
			<GButton
				:label="__('Send')"
				:pending="slipSending"
				:disabled="slipSending || !slipFile || !online"
				@click="sendSlip"
			/>
			<p v-if="!online" class="g-form-footer" role="status">
				{{ __("You need signal to send a time slip.") }}
			</p>
		</div>
	</GModal>
</template>

<script setup>
import { siteTime } from "@/utils/siteTime"
import { shiftGauge } from "@/utils/shiftGauge"
import { clockTime } from "@/utils/daySheet"
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from "vue"

import GButton from "@/components/glass/GButton.vue"
import GModal from "@/components/glass/GModal.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import TimeSlipFields from "@/components/TimeSlipFields.vue"
import { gToast } from "@/components/glass/toast"
import { useOnline } from "@/composables/useOnline"
import { nowResource } from "@/data/now"
import { firstMessage } from "@/utils/loudRequest"
import { attachSlipFile, sendTimeSlip, slipStatusLine } from "@/utils/timeSlip"

const __ = inject("$translate")
const employee = inject("$employee")
const online = useOnline()
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

//: The day's first check-in and the leave time, from the server (now.py
//: _leave_by: the shift end, later by however late they came in). On the site
//: clock, as `since` is.
const firstIn = computed(() => {
	const v = session.value?.first_in
	const t = v ? siteTime(v) : null
	return t?.isValid() ? t : null
})
const leaveTime = computed(() => {
	const v = session.value?.leave_by
	const t = v ? siteTime(v) : null
	return t?.isValid() ? t : null
})
const inAt = computed(() => (firstIn.value ? firstIn.value.format("h:mm a") : ""))
const leaveAt = computed(() => (leaveTime.value ? leaveTime.value.format("h:mm a") : ""))
const leaveHHMM = computed(() => (leaveTime.value ? leaveTime.value.format("HH:mm") : null))

const detail = computed(() => {
	if (!data.value.state && nowResource.error) return ""
	// The shift window, when there is one — that is the thing a person checks
	// the bar for after the state itself.
	// While working: when they came in and when they may leave (owner, 28 Sep
	// 2026: his screenshot had no check-in time, and late in means late out).
	if (stateKey.value === "working" && inAt.value && leaveAt.value) {
		return __("In {0} · leave at {1}", [inAt.value, leaveAt.value])
	}
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
	const [h, m] = String(data.value.time || "")
		.split(":")
		.map(Number)
	if (!Number.isFinite(h) || !Number.isFinite(m)) return null
	return (h * 60 + m + Math.floor((Date.now() - answeredAt.value) / 60000)) % (24 * 60)
})

//: Only while checked in with a shift window: that is when "how far through"
//: means something. Worked out from the window, never counted.
const gauge = computed(() =>
	stateKey.value === "working" && shift.value && nowMin.value !== null
		? shiftGauge({
				start: shift.value.start,
				end: shift.value.end,
				leaveBy: leaveHHMM.value,
				nowMin: nowMin.value,
		  })
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

//: The time slip, as the SERVER counts it (now.py _time_slip): its status once filed, or the
//: offer to file one when the day was late and none exists. The status word is slipStatusLine's;
//: its tone picks the chip the rest of the app already draws.
const slip = computed(() => data.value.time_slip || null)
const CHIPS = { warn: "attention", success: "success", danger: "danger" }
const slipLine = computed(() => {
	const line = slip.value?.status ? slipStatusLine(slip.value.status, __) : null
	return line ? { ...line, chip: CHIPS[line.tone] } : null
})
const slipOffered = computed(() => Number(slip.value?.late_minutes) > 0 && !slip.value?.name)
//: a waiting slip saved without its file (the upload failed): the file can still go
//: (review of c9a824c15: "Add the file from Today" led nowhere)
const slipNeedsFile = computed(
	() => Boolean(slip.value?.name) && slip.value.status === "Open" && !slip.value.has_file
)

const slipOpen = ref(false)
const slipFile = ref(null)
const slipSending = ref(false)

function closeSlip() {
	slipOpen.value = false
	slipFile.value = null
}

async function sendSlip() {
	if (slipSending.value || !slipFile.value || !slip.value) return
	slipSending.value = true
	try {
		if (slipNeedsFile.value) await attachSlipFile(slip.value.name, slipFile.value)
		else
			await sendTimeSlip({
				employee: employee.data?.name,
				day: slip.value.day,
				file: slipFile.value,
			})
		gToast({ title: __("Time slip sent"), variant: "success" })
		closeSlip()
	} catch (error) {
		console.warn("[NowBar] time slip not sent", error)
		// a failed upload has already said so (FileAttachment toasts); say only what is left
		if (!error?.slipName && !slipNeedsFile.value)
			gToast({
				title: __("Time slip not sent"),
				text: firstMessage(error, __("Could not send your time slip.")),
				variant: "error",
			})
		// saved without its file: the request exists, so the offer is over
		if (error?.slipName) closeSlip()
	} finally {
		slipSending.value = false
		await Promise.allSettled([nowResource.reload()])
	}
}

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

<style>
/* The time slip line and its quiet add button, last on the Today card. */
.g-now__slip {
	display: flex;
	align-items: center;
	gap: 6px;
	margin: 8px 0 0;
	font-family: var(--g-type-caption-family);
	font-size: var(--g-type-caption-size);
	line-height: var(--g-type-caption-line-height);
	color: var(--g-ink2);
}
.g-now__slip-add {
	min-height: var(--g-touch-target-min);
	margin: 0;
	padding: 0;
	border: 0;
	background: transparent;
	text-align: left;
	cursor: pointer;
	font-family: var(--g-type-caption-family);
	font-size: var(--g-type-caption-size);
	line-height: var(--g-type-caption-line-height);
	color: var(--g-ink2);
}
</style>
