<!--
  GProgressRing — KPI ring (spec §10.1 #9). Not a surface; it sits on one.
  88×88, r38, stroke 7, round cap, circumference 238.8,
  dashoffset = 238.8 × (1 − score/max), arc --brand, centre display 25/800
  tabular, svg rotated −90deg so the arc starts at 12 o'clock.
  Identical at both breakpoints (§20.7).

  Track is --track-solid, NOT --icon-bg: §6.3 overrides §10.1 #9's visual
  description — a performance rating must not be read through a moving tint.

  Announces as "Score 4.2 out of 5" (§14.1) — the numeral alone is not the
  signal, and the ring itself is decorative to assistive tech.

  Props:
    score    number, required
    max      number, default 5
    label    string, default "Score" — announcement prefix
    loading  boolean — §11.2 skeleton disc, no spinner
-->
<template>
	<div class="g-ring">
		<template v-if="loading">
			<GSkeleton width="88px" height="88px" radius="50%" />
		</template>
		<template v-else>
			<span class="g-sr">{{ label }} {{ score }} out of {{ max }}</span>
			<svg class="g-ring__svg" width="88" height="88" viewBox="0 0 88 88" aria-hidden="true">
				<circle class="g-ring__track" cx="44" cy="44" r="38" />
				<circle
					class="g-ring__arc"
					cx="44"
					cy="44"
					r="38"
					:stroke-dasharray="CIRCUMFERENCE"
					:stroke-dashoffset="dashoffset"
				/>
			</svg>
			<span class="g-ring__centre" aria-hidden="true">{{ score }}</span>
		</template>
	</div>
</template>

<script setup>
import { computed } from "vue"
import GSkeleton from "./GSkeleton.vue"

// spec §10.1 #9 states the circumference explicitly (2π × 38 = 238.76)
const CIRCUMFERENCE = 238.8

const props = defineProps({
	score: { type: Number, required: true },
	max: { type: Number, default: 5 },
	label: { type: String, default: "Score" },
	loading: { type: Boolean, default: false },
})

// clamped: a score above max would wrap the arc past 12 o'clock and read as a
// near-empty ring; a negative one would overdraw the track
const dashoffset = computed(() => {
	const fraction = props.max ? Math.min(1, Math.max(0, props.score / props.max)) : 0
	return CIRCUMFERENCE * (1 - fraction)
})
</script>
