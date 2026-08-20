<!--
  GCalendar — attendance calendar (spec §10.2 #18). ONE glass surface:
  radius-action 19px, pad 15px 13px, 7-col grid gap 4px, day 10.5px r8.
  Identical at both breakpoints (§20.7).

  Colour is never the only signal (§14.1): every state appears in the legend
  with a text label, and each day cell carries an accessible name naming its
  state ("14 August, on leave").

  Measured, composited over glass (light / dark):
    day numbers  --ink-muted            4.56 / 4.58  (text)
    present      --on-brand on --brand 16.63 light; --brand on brand-19% 8.65 dark
    on leave     --leave-ink on leave-26%  4.56 / 7.03
    rest day     --ink3 as a NON-TEXT border marker  3.07 / 3.61
  §14.4 exception 2: rest days carry no opacity multiplier and their numerals
  use --ink-muted like every other day — --ink3 marks the cell, never the text.

  Every day cell is a 44px touch target (§5) without moving the 10.5px numeral.

  Props:
    title      string, required — e.g. "August 2026"
    days       array, required — [{ day: 14, state: "present"|"leave"|"rest"|"absent"|"none" }]
    leadingBlanks number, default 0 — empty cells before day 1
    weekdays   array — 7 single-letter headers, defaults to Mon–Sun initials
    legend     array — [{ state, label }]; defaults to the four states above
  Emits: select(day) — day cells are buttons
-->
<template>
	<div class="g-glass g-cal">
		<div class="g-cal__head">
			<span class="g-cal__title">{{ title }}</span>
			<slot name="action" />
		</div>

		<div class="g-cal__grid" role="grid" :aria-label="title">
			<span v-for="(w, i) in weekdays" :key="`w${i}`" class="g-cal__dow" aria-hidden="true">
				{{ w }}
			</span>

			<span
				v-for="n in leadingBlanks"
				:key="`b${n}`"
				class="g-cal__day g-cal__day--empty"
				aria-hidden="true"
			/>

			<button
				v-for="d in days"
				:key="d.day"
				type="button"
				class="g-cal__day g-focusable"
				:class="`g-cal__day--${d.state}`"
				:aria-label="`${d.day} ${title}, ${stateLabel(d.state)}`"
				@click="$emit('select', d.day)"
			>
				{{ d.day }}
			</button>
		</div>

		<div class="g-cal__legend">
			<span v-for="key in legend" :key="key.state" class="g-cal__key">
				<span class="g-cal__swatch" :class="`g-cal__swatch--${key.state}`" aria-hidden="true" />
				{{ key.label }}
			</span>
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	title: { type: String, required: true },
	days: { type: Array, required: true },
	leadingBlanks: { type: Number, default: 0 },
	weekdays: { type: Array, default: () => ["M", "T", "W", "T", "F", "S", "S"] },
	legend: {
		type: Array,
		default: () => [
			{ state: "present", label: "Present" },
			{ state: "leave", label: "On leave" },
			{ state: "rest", label: "Rest day" },
			{ state: "absent", label: "Absent" },
		],
	},
})
defineEmits(["select"])

// the legend is the source of the spoken state name, so a caller that renames
// a state in the legend renames it in the announcement too
function stateLabel(state) {
	return props.legend.find((k) => k.state === state)?.label ?? "no record"
}
</script>
