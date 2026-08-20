<!--
  GBalanceCard — leave balance cell (spec §10.1 #6). A CELL, not a surface:
  it lives inside GBalanceGrid, which is the single glass panel (§15.2).
  pad-panel, radius-card 17px, number display 31/800/−0.02em tabular,
  label 10px/600/0.13em, 3px bar — track --track-solid, fill --brand + glow.
  The track is solid, NOT --icon-bg: §6.3 names leave balances, and the bar
  reads a balance, so it may not be read through a moving tint.
  Identical at both breakpoints (§20.7); only the parent grid reflows (§20.5).

  PRO-RATED HEADROOM BAND — ported from .m-bar-band (modernist.css). It marks
  the span between a pro-rated allocation and the full annual entitlement:
  headroom the employee does not get this year. Hatched at 45° so it can never
  be misread as earned balance, restyled to --ink3. Behaviour is unchanged:
  anchored right, width = proratedPercentage.

  Announces as "Annual leave, 7.5 days remaining of 8 allocated" (§14.1) —
  the visual figures are aria-hidden and the sentence is the accessible name.

  Props:
    label               string, required — e.g. "Annual leave"
    remaining           number, required — days left
    allocated           number, required — days allocated; the announced figure
    entitlement         number — gauge denominator when it exceeds `allocated`
                        (a pro-rated joiner). Defaults to `allocated`
    proratedPercentage  number, default 0 — band width 0–100; 0 hides the band
    unit                string, default "days" — announced unit only
  Slot:
    note  — qualifiers under the label, e.g. the pro-rated allocation or a
            carry-forward note. Aria-hidden with the rest of the visual block;
            put anything that must be announced into the label or the props.
-->
<template>
	<div class="g-cell">
		<span class="g-sr">{{ announcement }}</span>

		<div aria-hidden="true">
			<div class="g-balance__number">{{ remaining }}</div>
			<div class="g-balance__bar">
				<div class="g-balance__fill" :style="{ width: `${fillPercentage}%` }" />
				<div
					v-if="proratedPercentage > 0"
					class="g-balance__band"
					:style="{ width: `${proratedPercentage}%` }"
				/>
			</div>
			<div class="g-balance__label">{{ label }}</div>
			<!-- Real allocations carry qualifiers the mockup never showed:
			     "Pro-rated: 8 allocated for 2026", "incl. carry-forward". They
			     belong on the card, not beside it. -->
			<div v-if="$slots.note" class="g-balance__note"><slot name="note" /></div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue"

const props = defineProps({
	label: { type: String, required: true },
	remaining: { type: Number, required: true },
	allocated: { type: Number, required: true },
	// The gauge denominator, when it differs from what was allocated. A
	// pro-rated joiner is allocated 8 days of a 12-day annual entitlement: the
	// bar measures against 12 (which is what the hatched band spans), while the
	// announcement must say 8, because 8 is what they actually have.
	entitlement: { type: Number, default: 0 },
	proratedPercentage: { type: Number, default: 0 },
	unit: { type: String, default: "days" },
})

// guard against a zero or missing allocation — a 0/0 balance is a real state
// (allocation not yet run) and must not render NaN% or overflow the track
const fillPercentage = computed(() => {
	const denominator = props.entitlement || props.allocated
	if (!denominator) return 0
	return Math.min(100, Math.max(0, (props.remaining / denominator) * 100))
})

const announcement = computed(
	() => `${props.label}, ${props.remaining} ${props.unit} remaining of ${props.allocated} allocated`
)
</script>
